
"""
MY TECH LAB — Research Execution Engine V1

Responsibilities:
- Execute real web searches through Tavily.
- Preserve source URLs, dates, domains and retrieval timestamps.
- Deduplicate repeated search results.
- Track independent source domains.
- Report failures honestly instead of inventing evidence.

This module does not yet write to JSON storage or change opportunity
decisions. That integration belongs in main.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time

from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
)
from urllib.request import Request, urlopen


RESEARCH_EXECUTION_ENGINE_VERSION = (
    "RESEARCH_EXECUTION_ENGINE_V1_20261010"
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

DEFAULT_MAX_RESULTS = 5
MAX_ALLOWED_RESULTS = 10
REQUEST_TIMEOUT_SECONDS = 25


class ResearchExecutionError(Exception):
    """Raised when a research task cannot be executed."""


def utc_now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str:
    """Convert a value to clean, single-line text."""
    if value is None:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_url(url: str) -> str:
    """
    Remove fragments and common tracking parameters.

    This improves duplicate detection without treating every URL
    on the same website as the same article.
    """
    try:
        parsed = urlparse(url.strip())

        if parsed.scheme.lower() not in {"http", "https"}:
            return url.strip()

        tracking_prefixes = (
            "utm_",
            "fbclid",
            "gclid",
            "mc_cid",
            "mc_eid",
        )

        query_items = [
            (key, value)
            for key, value in parse_qsl(
                parsed.query,
                keep_blank_values=True,
            )
            if not key.lower().startswith(tracking_prefixes)
        ]

        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
            path=parsed.path.rstrip("/") or "/",
            query=urlencode(query_items),
            fragment="",
        )

        return urlunparse(normalized)

    except (TypeError, ValueError):
        return url.strip()


def extract_domain(url: str) -> str:
    """Return a normalized hostname for source-diversity checks."""
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower().strip(".")

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    except (TypeError, ValueError):
        return ""


def stable_finding_key(url: str, title: str) -> str:
    """Generate a repeatable identity for a search result."""
    normalized_url = normalize_url(url)

    identity = normalized_url or normalize_text(title).lower()

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def build_search_query(task: dict[str, Any]) -> str:
    """
    Build a query from the task's subject, geography and purpose.

    We keep the task's wording because it contains the actual
    question the opportunity engine wants answered.
    """
    subject = normalize_text(task.get("subject"))
    geography = normalize_text(task.get("geography"))
    task_text = normalize_text(task.get("task"))
    purpose = normalize_text(task.get("purpose"))

    parts = []

    if subject:
        parts.append(subject)

    if task_text:
        parts.append(task_text)

    if purpose and purpose.lower() not in task_text.lower():
        parts.append(purpose)

    if geography and geography.upper() not in {
        "GLOBAL",
        "WORLDWIDE",
        "N/A",
        "UNKNOWN",
    }:
        parts.append(geography)

    return " ".join(parts).strip()


def choose_search_depth(task: dict[str, Any]) -> str:
    """Map the existing research mode to Tavily search depth."""
    mode = normalize_text(
        task.get("research_mode", "STANDARD")
    ).upper()

    if mode == "DEEP":
        return "advanced"

    return "basic"


def request_tavily_search(
    query: str,
    api_key: str,
    search_depth: str = "basic",
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """Call Tavily's search API using Python's standard library."""
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": search_depth,
        "max_results": max(
            1,
            min(int(max_results), MAX_ALLOWED_RESULTS),
        ),
        "include_answer": False,
        "include_raw_content": False,
        "topic": "general",
    }

    request = Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MY-TECH-LAB/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            raw_body = response.read().decode("utf-8")
            result = json.loads(raw_body)

    except HTTPError as exc:
        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        # Avoid returning request headers or the API key.
        safe_body = error_body[:500]

        raise ResearchExecutionError(
            f"Tavily returned HTTP {exc.code}: {safe_body}"
        ) from None

    except URLError as exc:
        raise ResearchExecutionError(
            f"Network connection failed: {exc.reason}"
        ) from None

    except TimeoutError:
        raise ResearchExecutionError(
            "The search provider timed out."
        ) from None

    except json.JSONDecodeError:
        raise ResearchExecutionError(
            "The search provider returned invalid JSON."
        ) from None

    if not isinstance(result, dict):
        raise ResearchExecutionError(
            "The search provider returned an unexpected response."
        )

    return result


def normalize_findings(
    raw_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize and deduplicate provider results.

    Tavily's relevance score is retained as a search score only.
    It is NOT a source-trust score or probability that a claim is true.
    """
    findings = []
    seen_keys = set()

    for item in raw_results:
        if not isinstance(item, dict):
            continue

        title = normalize_text(item.get("title"))
        url = normalize_text(item.get("url"))
        content = normalize_text(item.get("content"))

        if not title or not url:
            continue

        normalized_url = normalize_url(url)
        key = stable_finding_key(normalized_url, title)

        if key in seen_keys:
            continue

        seen_keys.add(key)

        published_date = normalize_text(
            item.get("published_date")
        ) or None

        raw_score = item.get("score")

        try:
            search_score = float(raw_score)
        except (TypeError, ValueError):
            search_score = None

        findings.append(
            {
                "finding_key": key,
                "title": title,
                "url": normalized_url,
                "domain": extract_domain(normalized_url),
                "summary": content,
                "published_date": published_date,
                "retrieved_at": utc_now(),
                "search_score": search_score,
                "source_type": "WEB_SEARCH",
                "verification_status": "UNVERIFIED",
            }
        )

    return findings


def calculate_source_diversity(
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Count distinct domains, not articles.

    Multiple pages from the same publisher are not independent
    source confirmation. Domain diversity is only a first-pass
    check; it does not prove that publishers are independent.
    """
    domains = sorted(
        {
            finding.get("domain", "")
            for finding in findings
            if finding.get("domain")
        }
    )

    return {
        "unique_domain_count": len(domains),
        "domains": domains,
        "independent_confirmation": (
            "NOT_ESTABLISHED"
            if domains
            else "NO_SOURCES"
        ),
    }


def execute_research_task(
    task: dict[str, Any],
    api_key: str | None = None,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict[str, Any]:
    """
    Execute one research task.

    This function gathers and normalizes search results. It does not
    automatically declare claims true or recommend an investment.
    """
    started_at = utc_now()
    started_clock = time.monotonic()

    task_key = normalize_text(task.get("task_key"))
    query = build_search_query(task)

    if not task_key:
        return {
            "engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
            "status": "FAILED",
            "error": "The task is missing task_key.",
            "started_at": started_at,
            "completed_at": utc_now(),
        }

    if not query:
        return {
            "engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
            "task_key": task_key,
            "status": "FAILED",
            "error": "Could not build a search query from this task.",
            "started_at": started_at,
            "completed_at": utc_now(),
        }

    resolved_api_key = (
        api_key or os.getenv("TAVILY_API_KEY", "")
    ).strip()

    if not resolved_api_key:
        return {
            "engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
            "task_key": task_key,
            "status": "BLOCKED_CONFIGURATION",
            "error": (
                "TAVILY_API_KEY is not configured. "
                "Set the environment variable and retry."
            ),
            "query": query,
            "started_at": started_at,
            "completed_at": utc_now(),
        }

    search_depth = choose_search_depth(task)

    try:
        provider_response = request_tavily_search(
            query=query,
            api_key=resolved_api_key,
            search_depth=search_depth,
            max_results=max_results,
        )

        raw_results = provider_response.get("results", [])

        if not isinstance(raw_results, list):
            raise ResearchExecutionError(
                "The provider's results field was not a list."
            )

        findings = normalize_findings(raw_results)
        diversity = calculate_source_diversity(findings)

        if findings:
            status = "COMPLETED"
            error = None
        else:
            status = "NO_RESULTS"
            error = (
                "The search completed successfully but returned "
                "no usable results. This is not proof that no evidence exists."
            )

        return {
            "engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
            "task_key": task_key,
            "opportunity_key": task.get("opportunity_key"),
            "status": status,
            "error": error,
            "query": query,
            "search_depth": search_depth,
            "provider": "TAVILY",
            "started_at": started_at,
            "completed_at": utc_now(),
            "duration_seconds": round(
                time.monotonic() - started_clock,
                3,
            ),
            "result_count": len(findings),
            "findings": findings,
            "source_diversity": diversity,
            "limitations": [
                "Search relevance is not proof of factual accuracy.",
                "Search snippets may omit important context.",
                "Publication dates may be missing or provider-supplied.",
                "Different domains do not automatically mean independent reporting.",
                "Claims have not yet been checked for contradictions.",
            ],
        }

    except ResearchExecutionError as exc:
        return {
            "engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
            "task_key": task_key,
            "opportunity_key": task.get("opportunity_key"),
            "status": "FAILED",
            "error": str(exc),
            "query": query,
            "provider": "TAVILY",
            "started_at": started_at,
            "completed_at": utc_now(),
            "duration_seconds": round(
                time.monotonic() - started_clock,
                3,
            ),
            "result_count": 0,
            "findings": [],
        }
