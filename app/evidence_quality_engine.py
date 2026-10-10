
"""
MY TECH LAB — Evidence Quality Engine V1

Assesses research relevance, source authority, freshness,
source concentration, and possible conflicts.

IMPORTANT:
- A high score does NOT mean a claim is true.
- This engine does NOT automatically verify claims.
- All assessed findings remain UNVERIFIED until reviewed.
"""

from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re


EVIDENCE_QUALITY_ENGINE_VERSION = "EVIDENCE_QUALITY_ENGINE_V1_20261010"


STOP_WORDS = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on",
    "at", "by", "with", "from", "about", "is", "are", "was", "were",
    "be", "been", "being", "that", "this", "these", "those", "it",
    "as", "its", "their", "they", "them", "than", "into", "after",
    "before", "whether", "current", "latest", "relevant", "information",
    "research", "establish", "determine", "assess", "identify", "check",
    "verify", "seek", "independent", "corroboration", "material",
    "question", "task", "reduce", "gap", "potential", "opportunity",
    "market", "conditions", "new",
}

IRRELEVANT_PAGE_TERMS = {
    "privacy policy": "Privacy pages rarely answer investment valuation questions.",
    "privacy notice": "Privacy pages rarely answer investment valuation questions.",
    "contact us": "Contact pages are unlikely to provide decision-relevant evidence.",
    "careers": "Career pages are unlikely to answer the research question.",
    "job vacancy": "Job listings are unlikely to answer the research question.",
    "terms and conditions": "Terms pages are unlikely to answer the research question.",
}

POSITIVE_TERMS = {
    "growth", "increased", "increase", "improved", "profit", "profitable",
    "strong", "positive", "surplus", "upgrade", "rise", "rising",
}

NEGATIVE_TERMS = {
    "decline", "decreased", "decrease", "loss", "losses", "weak",
    "negative", "default", "impairment", "downgrade", "fall", "falling",
    "fraud", "risk", "deterioration",
}

TRACKING_PARAMETERS = {
    "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "source",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def tokenize(value):
    """Turn text into comparable, lowercase words."""
    words = re.findall(r"[a-z0-9]+", str(value or "").lower())
    return {word for word in words if word not in STOP_WORDS and len(word) > 1}


def normalize_url(url):
    """Remove URL fragments and common tracking parameters."""
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())
        filtered = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_PARAMETERS
        ]

        return urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/") or "/",
            "",
            urlencode(filtered),
            "",
        ))
    except Exception:
        return str(url).strip()


def get_domain(finding):
    """Prefer the stored domain, otherwise derive it from the URL."""
    domain = str(finding.get("domain") or "").lower().strip()

    if domain:
        return domain.removeprefix("www.")

    try:
        return urlparse(finding.get("url", "")).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def classify_source(finding):
    """Classify the apparent source type using its domain and title."""
    domain = get_domain(finding)
    title = str(finding.get("title") or "").lower()
    url = str(finding.get("url") or "").lower()

    if (
        domain.endswith(".gov")
        or domain.endswith(".go.tz")
        or "bot.go.tz" in domain
        or "dse.co.tz" in domain
        or "cmsa.go.tz" in domain
    ):
        return "GOVERNMENT_OR_REGULATOR"

    if (
        "financial statement" in title
        or "annual report" in title
        or "quarterly report" in title
        or "financial results" in title
        or url.endswith(".pdf")
    ):
        return "POTENTIAL_FINANCIAL_DOCUMENT"

    if any(term in title for term in ("privacy", "contact us", "careers")):
        return "LIKELY_LOW_RELEVANCE_PAGE"

    if any(term in domain for term in ("wikipedia.org", "rocketreach.co")):
        return "REFERENCE_OR_DIRECTORY"

    if any(term in title for term in ("stock exchange", "investor relations")):
        return "MARKET_OR_INVESTOR_SOURCE"

    if domain:
        return "OTHER_WEBSITE"

    return "UNKNOWN"


def score_source_authority(finding):
    """
    Score apparent source authority, not the truth of its claims.

    Company disclosures can be authoritative for what the company
    reported, but they are not independent confirmation of themselves.
    """
    domain = get_domain(finding)
    source_type = classify_source(finding)

    if source_type == "GOVERNMENT_OR_REGULATOR":
        score = 90
    elif source_type == "POTENTIAL_FINANCIAL_DOCUMENT":
        score = 75
    elif source_type == "MARKET_OR_INVESTOR_SOURCE":
        score = 75
    elif source_type == "REFERENCE_OR_DIRECTORY":
        score = 35
    elif source_type == "LIKELY_LOW_RELEVANCE_PAGE":
        score = 30
    elif source_type == "OTHER_WEBSITE":
        score = 45
    else:
        score = 20

    # A domain that appears to be the subject company's own site
    # may be primary evidence, but should not count as independent.
    title = str(finding.get("title") or "").lower()
    if "crdbbank.co.tz" in domain:
        if any(term in title for term in (
            "financial statement", "annual report", "quarterly",
            "financial results", "investor",
        )):
            score = max(score, 85)

    return score


def score_freshness(finding, task=None, now=None):
    """
    Score freshness using published_date when available.

    Retrieval time is NOT treated as publication time.
    Missing publication dates receive a low score, not an invented date.
    """
    now = now or datetime.now(timezone.utc)
    published = finding.get("published_date")

    if not published:
        return {
            "score": 20,
            "age_days": None,
            "status": "PUBLICATION_DATE_UNKNOWN",
            "reason": "No publication date supplied by the search result.",
        }

    try:
        text = str(published).strip()
        if len(text) == 4 and text.isdigit():
            published_dt = datetime(int(text), 1, 1, tzinfo=timezone.utc)
        else:
            published_dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if published_dt.tzinfo is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
            published_dt = published_dt.astimezone(timezone.utc)

        age_days = max(0, (now - published_dt).days)
    except (ValueError, TypeError, OverflowError):
        return {
            "score": 20,
            "age_days": None,
            "status": "PUBLICATION_DATE_UNPARSEABLE",
            "reason": "The publication date could not be interpreted safely.",
        }

    subject = str((task or {}).get("subject") or "").lower()
    research_text = (
        str((task or {}).get("task") or "")
        + " "
        + str((task or {}).get("purpose") or "")
    ).lower()

    time_sensitive = any(term in research_text for term in (
        "current price", "today", "latest price", "market price",
        "recent price", "live price",
    ))

    if time_sensitive:
        thresholds = [(7, 100), (30, 75), (90, 45), (180, 20)]
    else:
        thresholds = [(90, 100), (365, 80), (730, 55), (1825, 30)]

    score = 10
    for maximum_age, candidate_score in thresholds:
        if age_days <= maximum_age:
            score = candidate_score
            break

    return {
        "score": score,
        "age_days": age_days,
        "status": "DATED",
        "reason": f"Publication age: {age_days} days.",
    }


def score_relevance(finding, task):
    """Estimate how closely the result matches the research task."""
    title = str(finding.get("title") or "")
    summary = str(finding.get("summary") or "")
    subject = str(task.get("subject") or "")
    task_text = str(task.get("task") or "")
    purpose = str(task.get("purpose") or "")

    title_words = tokenize(title)
    content_words = tokenize(summary)
    subject_words = tokenize(subject)
    question_words = tokenize(task_text + " " + purpose)

    score = 0
    reasons = []

    subject_match = bool(subject_words and subject_words.intersection(
        title_words | content_words
    ))

    if subject_match:
        score += 40
        reasons.append("Subject appears in the result.")
    else:
        reasons.append("Subject was not clearly found in the title or summary.")

    if question_words:
        overlap = len(question_words.intersection(title_words | content_words))
        overlap_ratio = overlap / min(len(question_words), 12)
        score += min(40, round(overlap_ratio * 40))

    combined = (title + " " + summary).lower()
    for term, explanation in IRRELEVANT_PAGE_TERMS.items():
        if term in combined:
            score = min(score, 25)
            reasons.append(explanation)
            break

    if len(summary.strip()) < 80:
        score = min(score, 55)
        reasons.append("Very limited summary content.")

    return {
        "score": max(0, min(100, score)),
        "subject_match": subject_match,
        "reasons": reasons,
    }


def detect_potential_conflicts(findings):
    """
    Flag possible opposing language among results.

    This is a weak lexical screen, NOT a factual contradiction detector.
    Human review is required to determine whether claims refer to the
    same metric, period, unit and reporting basis.
    """
    conflicts = []

    for i, first in enumerate(findings):
        first_text = (
            str(first.get("title") or "") + " "
            + str(first.get("summary") or "")
        )
        first_words = tokenize(first_text)

        first_positive = first_words.intersection(POSITIVE_TERMS)
        first_negative = first_words.intersection(NEGATIVE_TERMS)

        for second in findings[i + 1:]:
            second_text = (
                str(second.get("title") or "") + " "
                + str(second.get("summary") or "")
            )
            second_words = tokenize(second_text)

            shared = first_words.intersection(second_words)
            shared -= POSITIVE_TERMS | NEGATIVE_TERMS

            if len(shared) < 3:
                continue

            second_positive = second_words.intersection(POSITIVE_TERMS)
            second_negative = second_words.intersection(NEGATIVE_TERMS)

            opposing_language = (
                (first_positive and second_negative)
                or (first_negative and second_positive)
            )

            if opposing_language:
                conflicts.append({
                    "finding_keys": [
                        first.get("finding_key"),
                        second.get("finding_key"),
                    ],
                    "status": "POSSIBLE_CONFLICT_REQUIRES_REVIEW",
                    "shared_terms": sorted(shared)[:10],
                    "warning": (
                        "Opposing language was detected. Check reporting "
                        "period, metric, units and context before concluding "
                        "that the sources contradict each other."
                    ),
                })

    return conflicts


def assess_findings(findings, task, now=None):
    """
    Assess a list of saved findings against one research task.

    Returns enriched copies; does not mutate input objects.
    Findings remain UNVERIFIED regardless of their score.
    """
    now = now or datetime.now(timezone.utc)
    findings = [dict(item) for item in findings]
    assessments = []

    # Count distinct domains. Multiple URLs on one domain do not
    # count as independent source domains.
    domain_counts = {}
    for finding in findings:
        domain = get_domain(finding)
        if domain:
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

    seen_urls = set()

    for finding in findings:
        url_key = normalize_url(finding.get("url"))
        domain = get_domain(finding)

        relevance = score_relevance(finding, task)
        authority = score_source_authority(finding)
        freshness = score_freshness(finding, task, now)

        duplicate = bool(url_key and url_key in seen_urls)
        if url_key:
            seen_urls.add(url_key)

        # Duplicate URLs receive no additional evidence value.
        independence = 100 if domain and domain_counts.get(domain, 0) == 1 else 40
        if not domain:
            independence = 20

        quality_score = round(
            relevance["score"] * 0.35
            + authority * 0.30
            + freshness["score"] * 0.20
            + independence * 0.15
        )

        flags = []
        if relevance["score"] < 35:
            flags.append("LOW_RELEVANCE")
        if freshness["status"] != "DATED":
            flags.append("FRESHNESS_UNKNOWN")
        if domain and domain_counts.get(domain, 0) > 1:
            flags.append("SOURCE_DOMAIN_REPEATED")
        if duplicate:
            flags.append("DUPLICATE_URL")
        if not finding.get("url"):
            flags.append("MISSING_SOURCE_URL")

        finding["evidence_quality"] = {
            "engine_version": EVIDENCE_QUALITY_ENGINE_VERSION,
            "score": quality_score,
            "score_meaning": (
                "Heuristic source-and-relevance assessment; not probability "
                "of truth, investment return, or successful opportunity."
            ),
            "relevance": relevance,
            "source_authority_score": authority,
            "source_type_estimate": classify_source(finding),
            "freshness": freshness,
            "domain": domain,
            "domain_occurrence_count": domain_counts.get(domain, 0),
            "independence_score": independence,
            "duplicate_url": duplicate,
            "flags": flags,
            "assessed_at": utc_now(),
        }

        # Do not automatically upgrade a finding to VERIFIED.
        finding["verification_status"] = "UNVERIFIED"
        finding["review_status"] = (
            "DUPLICATE"
            if duplicate
            else "REVIEW_REQUIRED"
        )

        assessments.append(finding)

    conflicts = detect_potential_conflicts(assessments)

    conflict_keys = {
        key
        for conflict in conflicts
        for key in conflict.get("finding_keys", [])
        if key
    }

    for finding in assessments:
        if finding.get("finding_key") in conflict_keys:
            finding["evidence_quality"]["flags"].append(
                "POSSIBLE_CONFLICT_REQUIRES_REVIEW"
            )

    return {
        "engine_version": EVIDENCE_QUALITY_ENGINE_VERSION,
        "task_key": task.get("task_key"),
        "opportunity_key": task.get("opportunity_key"),
        "assessed_count": len(assessments),
        "distinct_source_domains": len(domain_counts),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "findings": assessments,
        "important_note": (
            "Automated quality assessment is triage, not verification. "
            "Review primary documents and the underlying claims before "
            "using findings for a consequential decision."
        ),
    }
