
"""
MY TECH LAB — Research Task Engine V1

Creates persistent, deduplicated research tasks from opportunity candidates.
Creating a task does not mean its research has been completed.
"""

from datetime import datetime, timezone
import hashlib
import re


RESEARCH_TASK_ENGINE_VERSION = "RESEARCH_TASK_ENGINE_V1_20261010"

TERMINAL_TASK_STATUSES = {
    "COMPLETED",
    "CANCELLED",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value):
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip().casefold(),
    )


def make_task_key(opportunity_key, task_description):
    """Stable identity prevents duplicate tasks across repeated runs."""
    identity = (
        normalize_text(opportunity_key)
        + "|"
        + normalize_text(task_description)
    )

    return hashlib.sha256(
        identity.encode("utf-8")
    ).hexdigest()


def build_research_task(opportunity, research_item):
    task_description = str(
        research_item.get("task", "")
    ).strip()

    task_key = make_task_key(
        opportunity.get("opportunity_key", ""),
        task_description,
    )

    return {
        "task_key": task_key,
        "opportunity_key": opportunity.get("opportunity_key"),
        "opportunity_title": opportunity.get("title"),
        "subject": opportunity.get("subject", "Unknown"),
        "domain": opportunity.get("domain", "GENERAL"),
        "geography": opportunity.get("geography", "GLOBAL"),
        "task": task_description,
        "purpose": research_item.get(
            "purpose",
            "Reduce uncertainty before making a decision.",
        ),
        "research_mode": research_item.get(
            "research_mode",
            "STANDARD",
        ),
        "status": "OPEN",
        "source_signal_ids": opportunity.get(
            "source_signal_ids", []
        ),
        "source_observation_ids": opportunity.get(
            "source_observation_ids", []
        ),
        "evidence_observation_ids": [],
        "attempt_count": 0,
        "last_attempt_at": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "engine_version": RESEARCH_TASK_ENGINE_VERSION,
    }


def generate_research_tasks(opportunities, existing_tasks):
    """
    Add missing tasks without duplicating existing ones.

    Completed/cancelled tasks are never reopened automatically.
    Existing task history is preserved.
    """
    if not isinstance(opportunities, list):
        opportunities = []

    if not isinstance(existing_tasks, list):
        raise TypeError("existing_tasks must be a list")

    existing_by_key = {}

    for task in existing_tasks:
        if not isinstance(task, dict):
            continue

        key = task.get("task_key")
        if key:
            existing_by_key[key] = task

    created = 0
    updated = 0
    skipped = 0

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            skipped += 1
            continue

        opportunity_key = opportunity.get("opportunity_key")

        if not opportunity_key:
            skipped += 1
            continue

        research_items = opportunity.get("next_best_research", [])

        if not isinstance(research_items, list):
            skipped += 1
            continue

        for research_item in research_items:
            if not isinstance(research_item, dict):
                skipped += 1
                continue

            description = str(
                research_item.get("task", "")
            ).strip()

            if not description:
                skipped += 1
                continue

            candidate = build_research_task(
                opportunity,
                research_item,
            )

            task_key = candidate["task_key"]
            existing = existing_by_key.get(task_key)

            if existing is None:
                existing_tasks.append(candidate)
                existing_by_key[task_key] = candidate
                created += 1
                continue

            status = str(
                existing.get("status", "OPEN")
            ).strip().upper()

            if status in TERMINAL_TASK_STATUSES:
                skipped += 1
                continue

            # Refresh descriptive information while preserving task history.
            for field in (
                "opportunity_title",
                "subject",
                "domain",
                "geography",
                "purpose",
                "research_mode",
                "source_signal_ids",
                "source_observation_ids",
            ):
                existing[field] = candidate[field]

            existing["updated_at"] = utc_now()
            existing["engine_version"] = (
                RESEARCH_TASK_ENGINE_VERSION
            )

            updated += 1

    return {
        "research_task_engine_version": (
            RESEARCH_TASK_ENGINE_VERSION
        ),
        "opportunities_received": len(opportunities),
        "tasks_created": created,
        "tasks_updated": updated,
        "items_skipped": skipped,
        "total_tasks": len(existing_tasks),
    }
