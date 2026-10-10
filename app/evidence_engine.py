
"""
MY TECH LAB — EVIDENCE INTELLIGENCE ENGINE

Purpose:
- Assess whether a search result is relevant to its research question.
- Flag weak, stale, undated, or potentially duplicated evidence.
- Identify source-quality limitations.
- Produce a review priority and explain the reasons.
- Preserve the distinction between automated assessment and verification.

Important:
This engine does not prove that a claim is true.
Its scores are heuristic triage scores, not probabilities.
"""

from datetime import datetime, timezone
from urllib.parse import urlparse
import re


EVIDENCE_ENGINE_VERSION = "EVIDENCE_INTELLIGENCE_ENGINE_V1_20261010"


# ---------------------------------------------------------
# BASIC NORMALIZATION
# ---------------------------------------------------------

def normalize_text(value):
    """Convert text to a consistent form for comparisons."""
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().lower(),
    )


def tokenize(value):
    """Extract useful word tokens while ignoring very common words."""
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this",
        "into", "are", "was", "were", "has", "have", "had",
        "its", "their", "they", "them", "you", "your", "our",
        "about", "whether", "which", "what", "when", "where",
        "who", "how", "why", "can", "could", "would", "should",
        "may", "might", "will", "not", "but", "than", "then",
        "before", "after", "between", "through", "while",
        "independent", "evidence", "research", "information",
        "source", "sources", "result", "results",
    }

    words = re.findall(r"[a-z0-9]+", normalize_text(value))

    return {
        word for word in words
        if len(word) > 2 and word not in stop_words
    }


def get_domain(finding):
    """Prefer the stored domain, falling back to the URL hostname."""
    domain = normalize_text(finding.get("domain"))

    if domain:
        return domain.removeprefix("www.")

    url = str(finding.get("url") or "").strip()

    try:
        return urlparse(url).hostname.lower().removeprefix("www.") \
            if urlparse(url).hostname else ""
    except ValueError:
        return ""


# ---------------------------------------------------------
# SOURCE CLASSIFICATION
# ---------------------------------------------------------

def classify_source(domain, url=""):
    """
    Classify source type using transparent heuristics.

    A source category is not a guarantee of reliability.
    Even an official source may be old, incomplete, or irrelevant.
    """
    domain = normalize_text(domain)
    url = normalize_text(url)

    if not domain:
        return "UNKNOWN"

    if (
        domain.endswith(".gov")
        or ".gov." in domain
        or domain.endswith(".go.tz")
        or domain.endswith(".go.uk")
        or domain.endswith(".gov.uk")
    ):
        return "GOVERNMENT"

    if (
        domain.endswith(".edu")
        or domain.endswith(".ac.tz")
        or domain.endswith(".ac.uk")
    ):
        return "ACADEMIC"

    if (
        "crdbbank.co.tz" in domain
        or "nmbbank.co.tz" in domain
        or "dse.co.tz" in domain
        or "bot.go.tz" in domain
        or "cmsa.go.tz" in domain
        or "tra.go.tz" in domain
        or "nbs.go.tz" in domain
    ):
        return "PRIMARY_INSTITUTIONAL"

    if domain.endswith("sec.gov"):
        return "REGULATORY_FILING"

    if (
        "reuters.com" in domain
        or "bloomberg.com" in domain
        or "ft.com" in domain
        or "apnews.com" in domain
        or "bbc.com" in domain
        or "bbc.co.uk" in domain
    ):
        return "ESTABLISHED_NEWS"

    if (
        "wikipedia.org" in domain
        or "rocketreach.co" in domain
        or "zoominfo.com" in domain
        or "crunchbase.com" in domain
    ):
        return "REFERENCE_OR_AGGREGATOR"

    if (
        "facebook.com" in domain
        or "x.com" in domain
        or "twitter.com" in domain
        or "tiktok.com" in domain
        or "reddit.com" in domain
    ):
        return "SOCIAL_OR_COMMUNITY"

    if url.startswith("https://"):
        return "OTHER_WEB"

    return "UNKNOWN"


# ---------------------------------------------------------
# RELEVANCE ASSESSMENT
# ---------------------------------------------------------

def assess_relevance(finding, task):
    """
    Estimate topical relevance using overlap between the task and
    the finding's title and summary.

    This is a simple keyword heuristic, not semantic understanding.
    """
    subject = str(task.get("subject") or "")
    task_text = " ".join([
        str(task.get("task") or ""),
        str(task.get("purpose") or ""),
        str(task.get("opportunity_title") or ""),
    ])

    title = str(finding.get("title") or "")
    summary = str(finding.get("summary") or "")

    subject_tokens = tokenize(subject)
    task_tokens = tokenize(task_text)
    result_tokens = tokenize(f"{title} {summary}")

    reasons = []

    if not result_tokens:
        return {
            "score": 0,
            "level": "LOW",
            "reasons": ["The result contains no usable title or summary."],
        }

    subject_match = bool(subject_tokens & result_tokens)

    if subject_tokens and not subject_match:
        reasons.append(
            "The result does not clearly mention the research subject."
        )

    task_overlap = task_tokens & result_tokens
    task_coverage = (
        len(task_overlap) / len(task_tokens)
        if task_tokens else 0
    )

    score = 20

    if subject_match:
        score += 40

    score += min(40, round(task_coverage * 100))

    score = min(100, score)

    if score >= 70:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    if not task_overlap:
        reasons.append(
            "The title and summary contain little language related "
            "to the research task."
        )

    if not reasons:
        reasons.append(
            "The result appears topically relevant; its claims still "
            "require review."
        )

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
    }


# ---------------------------------------------------------
# FRESHNESS ASSESSMENT
# ---------------------------------------------------------

def parse_date(value):
    if not value:
        return None

    text = str(value).strip()

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed.astimezone(timezone.utc)

    except (ValueError, TypeError):
        pass

    for date_format in (
        "%Y-%m-%d",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(
                text,
                date_format,
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def assess_freshness(finding, task):
    """
    Estimate freshness from the published date when available.

    Retrieval time is not publication time. An old document found today
    must not be treated as newly published evidence.
    """
    published = parse_date(finding.get("published_date"))

    if published is None:
        return {
            "level": "UNKNOWN",
            "age_days": None,
            "reasons": [
                "No usable publication date was found. Freshness "
                "cannot be established from retrieval time alone."
            ],
        }

    now = datetime.now(timezone.utc)
    age_days = max(0, (now - published).days)

    task_text = normalize_text(
        f"{task.get('task', '')} {task.get('purpose', '')}"
    )

    time_sensitive = any(
        term in task_text
        for term in (
            "current price",
            "today",
            "latest",
            "this week",
            "market price",
            "price movement",
            "recent",
            "time-sensitive",
        )
    )

    if age_days <= 30:
        level = "FRESH"
    elif age_days <= 180:
        level = "AGING"
    elif age_days <= 365:
        level = "OLD"
    else:
        level = "STALE"

    reasons = []

    if time_sensitive and age_days > 30:
        reasons.append(
            "The research task is time-sensitive, but this source "
            "is more than 30 days old."
        )

    if age_days > 365:
        reasons.append(
            "The source is more than one year old; confirm whether "
            "its claims remain valid."
        )

    if not reasons:
        reasons.append(
            f"The publication date indicates an age of {age_days} days. "
            "Relevance and continued validity still need review."
        )

    return {
        "level": level,
        "age_days": age_days,
        "reasons": reasons,
    }


# ---------------------------------------------------------
# DUPLICATE / SOURCE CONCENTRATION CHECK
# ---------------------------------------------------------

def assess_source_concentration(finding, all_findings):
    """
    Detect whether many saved results come from the same domain.

    This is not a claim that two different domains are independent.
    They may repeat the same press release or original report.
    """
    domain = get_domain(finding)

    same_domain = [
        item for item in all_findings
        if get_domain(item) == domain and domain
    ]

    distinct_domains = {
        get_domain(item)
        for item in all_findings
        if get_domain(item)
    }

    reasons = []

    if domain and len(same_domain) > 1:
        reasons.append(
            f"{len(same_domain)} saved findings come from {domain}; "
            "do not count them as independent corroboration."
        )

    if len(distinct_domains) <= 1:
        reasons.append(
            "The available findings currently cover only one source "
            "domain, or no domain could be identified."
        )

    if not reasons:
        reasons.append(
            "The saved collection includes multiple domains, but "
            "independent reporting has not been established."
        )

    return {
        "domain": domain or None,
        "same_domain_count": len(same_domain),
        "distinct_domain_count": len(distinct_domains),
        "reasons": reasons,
    }


# ---------------------------------------------------------
# OVERALL EVIDENCE ASSESSMENT
# ---------------------------------------------------------

def assess_finding(finding, task, all_findings):
    """
    Assess a single finding without changing its verification status.
    """
    domain = get_domain(finding)
    url = str(finding.get("url") or "")

    source_type = classify_source(domain, url)
    relevance = assess_relevance(finding, task)
    freshness = assess_freshness(finding, task)
    concentration = assess_source_concentration(
        finding,
        all_findings,
    )

    flags = []

    if source_type in {
        "UNKNOWN",
        "OTHER_WEB",
        "REFERENCE_OR_AGGREGATOR",
        "SOCIAL_OR_COMMUNITY",
    }:
        flags.append("SOURCE_NEEDS_REVIEW")

    if relevance["level"] == "LOW":
        flags.append("LOW_RELEVANCE")

    if freshness["level"] in {"UNKNOWN", "OLD", "STALE"}:
        flags.append("FRESHNESS_NEEDS_REVIEW")

    if concentration["same_domain_count"] > 1:
        flags.append("SOURCE_CONCENTRATION")

    if not url.startswith("https://"):
        flags.append("URL_NEEDS_REVIEW")

    # Heuristic triage score only. It is not a probability that the
    # finding is accurate, and it must not be used alone for investing.
    score = (
        relevance["score"] * 0.55
        + (
            100 if source_type in {
                "GOVERNMENT",
                "ACADEMIC",
                "PRIMARY_INSTITUTIONAL",
                "REGULATORY_FILING",
                "ESTABLISHED_NEWS",
            }
            else 50 if source_type == "OTHER_WEB"
            else 25
        ) * 0.30
        + (
            100 if freshness["level"] == "FRESH"
            else 70 if freshness["level"] == "AGING"
            else 35 if freshness["level"] == "OLD"
            else 20 if freshness["level"] == "STALE"
            else 40
        ) * 0.15
    )

    score = round(max(0, min(100, score)), 1)

    if relevance["level"] == "LOW":
        priority = "LOW_VALUE"
    elif score >= 70 and not (
        "FRESHNESS_NEEDS_REVIEW" in flags
    ):
        priority = "REVIEW_FIRST"
    elif score >= 45:
        priority = "REVIEW"
    else:
        priority = "LOW_PRIORITY"

    reasons = (
        relevance["reasons"]
        + freshness["reasons"]
        + concentration["reasons"]
    )

    if source_type == "PRIMARY_INSTITUTIONAL":
        reasons.append(
            "This appears to be an institutional source. Confirm the "
            "document date and whether it directly supports the claim."
        )

    if source_type == "REGULATORY_FILING":
        reasons.append(
            "This appears to be a regulatory filing, but check its date "
            "and whether it relates to the current question."
        )

    return {
        "evidence_engine_version": EVIDENCE_ENGINE_VERSION,
        "finding_key": finding.get("finding_key"),
        "finding_id": finding.get("id"),
        "title": finding.get("title"),
        "url": url,
        "domain": domain or None,
        "source_type": source_type,
        "relevance": relevance,
        "freshness": freshness,
        "source_concentration": concentration,
        "triage_score": score,
        "review_priority": priority,
        "flags": flags,
        "reasons": reasons,
        "verification_status": finding.get(
            "verification_status",
            "UNVERIFIED",
        ),
        "review_status": finding.get("review_status", "UNVERIFIED"),
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Automated assessment does not verify factual accuracy.",
            "Different domains do not necessarily mean independent sources.",
            "No publication date means freshness is unknown.",
            "The triage score is not a probability of truth or investment return.",
        ],
    }
