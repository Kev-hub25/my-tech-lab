"""
MY TECH LAB — Opportunity Engine

Converts detected signals into traceable opportunity candidates.
This module does not make investment decisions or claim returns are guaranteed.
"""

from datetime import datetime, timezone
import re


OPPORTUNITY_ENGINE_VERSION = "OPPORTUNITY_ENGINE_V1_20261010"

TERMINAL_STATUSES = {
    "REJECTED",
    "EXPIRED",
    "MISSED",
    "LEARNED",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def as_number(value, default=0):
    """Safely convert values to numbers."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def as_int(value, default=0):
    return int(as_number(value, default))


def clean_text(value, default="Unknown"):
    if value is None:
        return default

    result = str(value).strip()
    return result if result else default


def normalize_identity(value):
    """Normalize identity fields so repeated runs do not create duplicates."""
    return re.sub(
        r"\s+",
        " ",
        clean_text(value, "").strip().upper()
    )


def opportunity_key(signal):
    """
    Stable identity for an opportunity.

    Observation IDs are deliberately excluded because new evidence
    should update an existing opportunity rather than create another one.
    """
    parts = [
        signal.get("signal_type", ""),
        signal.get("subject", ""),
        signal.get("domain", ""),
        signal.get("geography", ""),
    ]

    return "|".join(normalize_identity(part) for part in parts)


def classify_opportunity(signal):
    signal_type = normalize_identity(signal.get("signal_type"))
    domain = normalize_identity(signal.get("domain"))
    subject = normalize_identity(signal.get("subject"))

    if (
        "FINANCIAL" in domain
        or "STOCK" in domain
        or "INVESTMENT" in domain
        or "VALUATION" in signal_type
        or "VALUE_DISLOCATION" in signal_type
    ):
        return "INVESTMENT"

    if any(word in domain for word in ("CRYPTO", "FOREX", "TRADING")):
        return "TRADING"

    if any(word in domain for word in ("TECH", "SOFTWARE", "AI", "DIGITAL")):
        return "TECH"

    if any(word in domain for word in ("BUSINESS", "CONSUMER", "RETAIL")):
        return "BUSINESS"

    if any(word in subject for word in ("DOMAIN NAME", "DOMAIN PORTFOLIO")):
        return "BUSINESS"

    return "GENERAL"


def build_thesis(signal):
    description = clean_text(
        signal.get("description"),
        "A detected signal may indicate a potential opportunity."
    )

    return description


def build_economic_mechanism(signal, opportunity_type):
    subject = clean_text(signal.get("subject"), "The subject")

    if opportunity_type == "INVESTMENT":
        return (
            f"Potential financial return could arise if the market price "
            f"of {subject} changes as investors incorporate new information "
            f"about its underlying business performance. A price decline "
            f"alone does not establish undervaluation."
        )

    if opportunity_type == "TRADING":
        return (
            f"Potential trading value in {subject} would depend on a "
            "testable price movement, a defined entry and exit, transaction "
            "costs, liquidity, and controlled downside risk."
        )

    if opportunity_type == "TECH":
        return (
            f"Potential value could be captured by using technology related "
            f"to {subject} to solve a real problem, reduce costs, save time, "
            "or create a product customers are willing to pay for."
        )

    if opportunity_type == "BUSINESS":
        return (
            f"Potential value could come from meeting a customer need related "
            f"to {subject} at a price that exceeds delivery, operating, "
            "acquisition, and financing costs."
        )

    return (
        f"The potential economic mechanism for {subject} has not yet been "
        "established. Research must identify who benefits, who pays, and "
        "why the value can be captured."
    )


def calculate_market_score(signal):
    """
    Heuristic attractiveness score from 0 to 100.

    This is not a probability of success, a valuation, or a return forecast.
    """
    strength = max(0, min(10, as_number(signal.get("strength"))))
    evidence_quality = max(
        0, min(10, as_number(signal.get("evidence_quality")))
    )
    source_diversity = max(
        0, min(10, as_number(signal.get("source_diversity")))
    )
    persistence = max(
        0, min(10, as_number(signal.get("persistence")))
    )

    return round(
        strength * 3
        + evidence_quality * 3
        + source_diversity * 2
        + persistence * 2,
        1,
    )


def calculate_research_mode(signal):
    strength = as_number(signal.get("strength"))
    confidence = as_number(signal.get("confidence"))
    importance = as_number(signal.get("importance"))

    description = normalize_identity(signal.get("description"))

    if any(
        word in description
        for word in ("URGENT", "EXPIRING", "TIME-SENSITIVE", "DEADLINE")
    ):
        return "TIME_SENSITIVE"

    if strength >= 8 or importance >= 9:
        return "DEEP"

    if confidence >= 7 and strength >= 5:
        return "STANDARD"

    return "FAST"


def build_requirements(signal, opportunity_type):
    if opportunity_type == "INVESTMENT":
        return [
            "Verify the latest market price, trading date, and price history.",
            "Verify recent financial statements and earnings growth.",
            "Assess valuation using appropriate financial metrics and peers.",
            "Review dividends, debt, cash flow, governance, and material news.",
            "Estimate downside, liquidity, transaction costs, and time horizon.",
            "Check available capital, emergency reserves, and risk tolerance "
            "before considering any investment decision.",
        ]

    if opportunity_type == "TRADING":
        return [
            "Define the setup and independently verify current market data.",
            "Specify entry, exit, invalidation, and maximum loss in advance.",
            "Estimate fees, spreads, slippage, liquidity, and execution risk.",
            "Test the approach on sufficient historical or simulated data.",
        ]

    if opportunity_type == "TECH":
        return [
            "Identify the specific user and problem.",
            "Find evidence that the problem is frequent and costly enough.",
            "Review existing competitors and alternative solutions.",
            "Estimate build cost, operating cost, pricing, and distribution.",
            "Validate demand before committing substantial resources.",
        ]

    if opportunity_type == "BUSINESS":
        return [
            "Identify target customers and the problem being solved.",
            "Verify demand, competitors, pricing, and customer acquisition.",
            "Estimate startup capital, operating costs, and gross margins.",
            "Check suppliers, logistics, regulations, and payment collection.",
            "Test demand before committing substantial resources.",
        ]

    return [
        "Clarify the opportunity and the target beneficiary.",
        "Establish the mechanism for creating and capturing economic value.",
        "Verify demand, cost, risk, and resource requirements.",
        "Define evidence that would justify proceeding or rejecting it.",
    ]


def build_information_gaps(signal, research, opportunity_type):
    gaps = []
    signal_type = normalize_identity(signal.get("signal_type"))

    if not signal.get("observation_ids"):
        gaps.append(
            "Trace the signal to specific supporting research observations."
        )

    related = [
        item
        for item in research
        if normalize_identity(item.get("subject"))
        == normalize_identity(signal.get("subject"))
        and normalize_identity(item.get("domain"))
        == normalize_identity(signal.get("domain"))
    ]

    if not related:
        gaps.append(
            "Find and verify supporting evidence for this subject and domain."
        )

    if opportunity_type == "INVESTMENT":
        types = {
            normalize_identity(item.get("observation_type"))
            for item in related
        }

        if not any("PRICE" in item for item in types):
            gaps.append("Verify the current market price and recent price history.")

        if not any(
            word in item
            for item in types
            for word in ("FUNDAMENTAL", "EARNINGS", "FINANCIAL")
        ):
            gaps.append(
                "Verify current financial results and business fundamentals."
            )

        gaps.append(
            "Establish whether the price movement is justified by valuation, "
            "business risks, market conditions, or new information."
        )

    elif opportunity_type == "BUSINESS":
        gaps.extend([
            "Establish evidence of customer demand and willingness to pay.",
            "Estimate realistic unit economics and customer acquisition costs.",
        ])

    elif opportunity_type == "TECH":
        gaps.extend([
            "Validate the problem with potential users or buyers.",
            "Assess whether existing tools already solve the problem adequately.",
        ])

    if as_number(signal.get("source_diversity")) < 3:
        gaps.append(
            "Seek independent corroboration; multiple observations from one "
            "source do not count as independent source confirmation."
        )

    if "VALUE_DISLOCATION" in signal_type:
        gaps.append(
            "Compare price movement with earnings quality, valuation, "
            "and relevant company or market news."
        )

    # Keep each gap once, preserving its original order.
    return list(dict.fromkeys(gaps))


def build_next_best_research(signal, gaps, opportunity_type):
    subject = clean_text(signal.get("subject"), "the subject")

    if not gaps:
        return [
            f"Review the accumulated evidence on {subject} and decide "
            "whether the candidate meets the criteria for the next stage."
        ]

    tasks = []

    for gap in gaps[:6]:
        tasks.append({
            "subject": subject,
            "task": gap,
            "purpose": (
                "Reduce a material information gap before committing "
                "money, time, or other resources."
            ),
            "research_mode": (
                "DEEP" if opportunity_type == "INVESTMENT" else "STANDARD"
            ),
            "completed": False,
        })

    return tasks


def calculate_priority_score(
    market_score,
    confidence_score,
    research_mode,
    information_gap_count,
):
    """
    A triage score, not a prediction of profitability.

    High confidence and attractiveness raise priority. A large number of
    unresolved gaps slightly reduces it. Personal capture is not guessed.
    """
    confidence = max(0, min(10, as_number(confidence_score))) * 5

    mode_adjustment = {
        "TIME_SENSITIVE": 10,
        "DEEP": 3,
        "STANDARD": 0,
        "FAST": -3,
    }.get(research_mode, 0)

    gap_adjustment = min(20, max(0, information_gap_count) * 2)

    score = (
        market_score * 0.5
        + confidence * 0.5
        + mode_adjustment
        - gap_adjustment
    )

    return round(max(0, min(100, score)), 1)


def find_existing_opportunity(opportunities, key):
    for opportunity in opportunities:
        if opportunity.get("opportunity_key") == key:
            return opportunity

    return None


def build_opportunity_from_signal(signal, research):
    opportunity_type = classify_opportunity(signal)
    gaps = build_information_gaps(signal, research, opportunity_type)
    research_mode = calculate_research_mode(signal)
    market_score = calculate_market_score(signal)
    confidence_score = max(
        0, min(10, as_number(signal.get("confidence")))
    )

    related_observations = [
        item for item in research
        if item.get("id") in (signal.get("observation_ids") or [])
    ]

    observation_ids = sorted({
        item.get("id")
        for item in related_observations
        if item.get("id") is not None
    })

    signal_id = signal.get("id")
    signal_ids = [signal_id] if signal_id is not None else []

    subject = clean_text(signal.get("subject"))
    domain = clean_text(signal.get("domain"))
    geography = clean_text(signal.get("geography"))

    priority_score = calculate_priority_score(
        market_score=market_score,
        confidence_score=confidence_score,
        research_mode=research_mode,
        information_gap_count=len(gaps),
    )

    return {
        "opportunity_key": opportunity_key(signal),
        "title": f"Potential {opportunity_type.title()} Opportunity: {subject}",
        "opportunity_type": opportunity_type,
        "subject": subject,
        "domain": domain,
        "geography": geography,
        "source_signal_ids": signal_ids,
        "source_observation_ids": observation_ids,
        "source_report_names": sorted({
            clean_text(item.get("source_report"))
            for item in related_observations
            if item.get("source_report")
        }),
        "thesis": build_thesis(signal),
        "economic_mechanism": build_economic_mechanism(
            signal, opportunity_type
        ),
        "market_score": market_score,
        "confidence_score": confidence_score,
        "personal_capture_score": None,
        "research_mode": research_mode,
        "status": "QUALIFYING",
        "decision": "INVESTIGATE",
        "requirements": build_requirements(signal, opportunity_type),
        "information_gaps": gaps,
        "next_best_research": build_next_best_research(
            signal, gaps, opportunity_type
        ),
        "priority_score": priority_score,
        "downside": [
            "The signal may be incomplete, stale, duplicated, or misleading.",
            "The apparent opportunity may not produce a positive net return.",
            "Time, capital, access, and execution constraints may prevent capture.",
        ],
        "kill_conditions": [
            "Reject if reliable evidence contradicts the core thesis.",
            "Reject if the economic mechanism cannot be demonstrated.",
            "Reject if realistic downside exceeds the acceptable risk limit.",
        ],
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "engine_version": OPPORTUNITY_ENGINE_VERSION,
    }


def generate_opportunities_from_signals(
    signals,
    research,
    existing_opportunities,
):
    """
    Convert detected signals into opportunity candidates.

    Mutates existing_opportunities in place so the caller can save the
    same list using the existing save_opportunities() function.
    """
    if not isinstance(signals, list):
        signals = []

    if not isinstance(research, list):
        research = []

    if not isinstance(existing_opportunities, list):
        raise TypeError("existing_opportunities must be a list")

    created = 0
    updated = 0
    skipped = 0

    for signal in signals:
        if not isinstance(signal, dict):
            skipped += 1
            continue

        if normalize_identity(signal.get("status")) not in {
            "DETECTED",
            "ACTIVE",
            "CONFIRMED",
        }:
            skipped += 1
            continue

        key = opportunity_key(signal)

        if not key.replace("|", "").strip():
            skipped += 1
            continue

        candidate = build_opportunity_from_signal(signal, research)
        existing = find_existing_opportunity(
            existing_opportunities, key
        )

        if existing is None:
            existing_opportunities.append(candidate)
            created += 1
            continue

        # Preserve lifecycle decisions and creation history.
        if normalize_identity(existing.get("status")) in TERMINAL_STATUSES:
            skipped += 1
            continue

        created_at = existing.get("created_at", candidate["created_at"])
        preserved_fields = {
            field: existing[field]
            for field in (
                "status",
                "decision",
                "personal_capture_score",
                "user_constraints",
                "resource_assessment",
                "outcome",
                "notes",
            )
            if field in existing
        }

        existing.update(candidate)
        existing.update(preserved_fields)
        existing["created_at"] = created_at
        existing["updated_at"] = utc_now()
        updated += 1

    return {
        "opportunity_engine_version": OPPORTUNITY_ENGINE_VERSION,
        "signals_received": len(signals),
        "opportunities_created": created,
        "opportunities_updated": updated,
        "signals_skipped": skipped,
        "total_opportunities": len(existing_opportunities),
    }