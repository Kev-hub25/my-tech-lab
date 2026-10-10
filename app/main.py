
from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.opportunity_engine import (
    OPPORTUNITY_ENGINE_VERSION,
    generate_opportunities_from_signals,
)
from app.research_task_engine import (
    RESEARCH_TASK_ENGINE_VERSION,
    generate_research_tasks,
)
from app.research_execution_engine import execute_research_task


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

PROJECTS_FILE = BASE_DIR / "projects.json"
OPPORTUNITIES_FILE = BASE_DIR / "opportunities.json"
RESEARCH_FILE = BASE_DIR / "research.json"
RESEARCH_REPORTS_FILE = BASE_DIR / "research_reports.json"
RESEARCH_FEEDS_FILE = BASE_DIR / "research_feeds.json"
SIGNALS_FILE = BASE_DIR / "signals.json"
RESEARCH_TASKS_FILE = BASE_DIR / "research_tasks.json"
RESEARCH_EXECUTIONS_FILE = BASE_DIR / "research_executions.json"
RESEARCH_FINDINGS_FILE = BASE_DIR / "research_findings.json"

SIGNAL_ENGINE_VERSION = "SIGNAL_ENGINE_V2_20261008"
RESEARCH_EXECUTION_ENGINE_VERSION = "RESEARCH_EXECUTION_ENGINE_V1_20261010"

app = FastAPI(title="MY TECH LAB")

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)


# ---------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------

class ResearchRecord(BaseModel):
    source: str
    domain: str
    subject: str
    observation: str

    observation_type: str = "GENERAL"
    direction: str = "NEUTRAL"
    magnitude: str | None = None
    geography: str = "GLOBAL"

    data: dict[str, Any] = Field(default_factory=dict)

    evidence_url: str | None = None
    source_report: str | None = None

    confidence: int = Field(default=5, ge=1, le=10)
    importance: int = Field(default=5, ge=1, le=10)


class ResearchFeed(BaseModel):
    name: str
    source_type: str = "CHATGPT_AUTOMATION"
    description: str = ""
    domain: str
    status: str = "ACTIVE"


class ResearchReport(BaseModel):
    feed: str
    title: str
    content: str
    domain: str
    geography: str = "GLOBAL"
    report_date: str
    source_reference: str | None = None


class Signal(BaseModel):
    signal_type: str
    title: str
    description: str
    subject: str
    domain: str

    geography: str = "GLOBAL"
    observation_ids: list[int] = Field(default_factory=list)

    strength: int = Field(default=5, ge=1, le=10)
    confidence: int = Field(default=5, ge=1, le=10)
    evidence_quality: int = Field(default=5, ge=1, le=10)
    source_diversity: int = Field(default=1, ge=1, le=10)
    persistence: int = Field(default=1, ge=1, le=10)

    status: str = "DETECTED"


# ---------------------------------------------------------
# GENERIC JSON STORAGE
# ---------------------------------------------------------

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json_list(file_path: Path):
    """Load a JSON list safely."""
    if not file_path.exists():
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, list) else []

    except (json.JSONDecodeError, OSError):
        return []


def save_json_list(file_path: Path, data):
    """Save through a temporary file to reduce partial writes."""
    temporary_file = file_path.with_suffix(".tmp")

    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    temporary_file.replace(file_path)


# ---------------------------------------------------------
# PROJECT DATA
# ---------------------------------------------------------

def load_projects():
    return load_json_list(PROJECTS_FILE)


def save_projects(projects):
    save_json_list(PROJECTS_FILE, projects)


# ---------------------------------------------------------
# OPPORTUNITY DATA
# ---------------------------------------------------------

def load_opportunities():
    return load_json_list(OPPORTUNITIES_FILE)


def save_opportunities(opportunities):
    save_json_list(OPPORTUNITIES_FILE, opportunities)


# ---------------------------------------------------------
# RESEARCH DATA
# ---------------------------------------------------------

def load_research():
    return load_json_list(RESEARCH_FILE)


def save_research(research):
    save_json_list(RESEARCH_FILE, research)


# ---------------------------------------------------------
# RAW RESEARCH REPORT DATA
# ---------------------------------------------------------

def load_research_reports():
    return load_json_list(RESEARCH_REPORTS_FILE)


def save_research_reports(reports):
    save_json_list(RESEARCH_REPORTS_FILE, reports)


# ---------------------------------------------------------
# RESEARCH FEED DATA
# ---------------------------------------------------------

def load_research_feeds():
    return load_json_list(RESEARCH_FEEDS_FILE)


def save_research_feeds(feeds):
    save_json_list(RESEARCH_FEEDS_FILE, feeds)


def build_research_feeds():
    feeds = load_research_feeds()
    reports = load_research_reports()
    research = load_research()

    enriched_feeds = []

    for feed in feeds:
        feed_name = feed.get("name", "")

        feed_reports = [
            report for report in reports
            if report.get("feed") == feed_name
        ]

        feed_observations = [
            record for record in research
            if record.get("source") == feed_name
        ]

        timestamps = (
            [
                report.get("received_at")
                for report in feed_reports
                if report.get("received_at")
            ]
            +
            [
                record.get("timestamp")
                for record in feed_observations
                if record.get("timestamp")
            ]
        )

        enriched_feed = dict(feed)
        enriched_feed["report_count"] = len(feed_reports)
        enriched_feed["observation_count"] = len(feed_observations)
        enriched_feed["last_updated"] = max(timestamps) if timestamps else None

        enriched_feeds.append(enriched_feed)

    return enriched_feeds


# ---------------------------------------------------------
# SIGNAL DATA
# ---------------------------------------------------------

def load_signals():
    return load_json_list(SIGNALS_FILE)


def save_signals(signals):
    save_json_list(SIGNALS_FILE, signals)


# ---------------------------------------------------------
# RESEARCH TASK DATA
# ---------------------------------------------------------

def load_research_tasks():
    return load_json_list(RESEARCH_TASKS_FILE)


def save_research_tasks(tasks):
    save_json_list(RESEARCH_TASKS_FILE, tasks)


# ---------------------------------------------------------
# RESEARCH EXECUTION HISTORY
# ---------------------------------------------------------

def load_research_executions():
    return load_json_list(RESEARCH_EXECUTIONS_FILE)


def save_research_executions(executions):
    save_json_list(RESEARCH_EXECUTIONS_FILE, executions)


# ---------------------------------------------------------
# RESEARCH FINDINGS
# ---------------------------------------------------------

def load_research_findings():
    return load_json_list(RESEARCH_FINDINGS_FILE)


def save_research_findings(findings):
    save_json_list(RESEARCH_FINDINGS_FILE, findings)


# ---------------------------------------------------------
# SIGNAL ENGINE V2 — EVIDENCE SCORING
# ---------------------------------------------------------

def get_observation_type(observation):
    return str(observation.get("observation_type", "GENERAL")).upper()


def get_direction(observation):
    return str(observation.get("direction", "NEUTRAL")).upper()


def get_source(observation):
    return str(observation.get("source", "")).strip().upper()


def calculate_evidence_quality(observations):
    if not observations:
        return 1

    scores = []

    for observation in observations:
        confidence = int(observation.get("confidence", 5))
        importance = int(observation.get("importance", 5))

        score = (confidence + importance) / 2

        if observation.get("data"):
            score += 1

        if observation.get("evidence_url") or observation.get("source_report"):
            score += 1

        scores.append(min(score, 10))

    return max(1, min(10, round(sum(scores) / len(scores))))


def calculate_source_diversity(observations):
    sources = {
        get_source(observation)
        for observation in observations
        if get_source(observation)
    }

    source_count = len(sources)

    if source_count <= 0:
        return 1
    if source_count == 1:
        return 2
    if source_count == 2:
        return 5
    if source_count == 3:
        return 7

    return 10


def calculate_persistence(observations):
    """Temporary proxy based on observation count."""
    observation_count = len(observations)

    if observation_count >= 5:
        return 10
    if observation_count == 4:
        return 8
    if observation_count == 3:
        return 6
    if observation_count == 2:
        return 4

    return 1


def calculate_signal_strength(
    evidence_quality,
    source_diversity,
    persistence,
    pattern_bonus=0,
):
    score = (
        evidence_quality * 0.50
        + source_diversity * 0.25
        + persistence * 0.25
        + pattern_bonus
    )

    return max(1, min(10, round(score)))


def calculate_signal_confidence(evidence_quality, source_diversity):
    score = evidence_quality * 0.60 + source_diversity * 0.40
    return max(1, min(10, round(score)))


# ---------------------------------------------------------
# VALUE DISLOCATION DETECTOR
# ---------------------------------------------------------

def detect_value_dislocation(observations):
    negative_price = [
        item for item in observations
        if get_observation_type(item) == "PRICE_CHANGE"
        and get_direction(item) == "NEGATIVE"
    ]

    positive_fundamentals = [
        item for item in observations
        if get_observation_type(item)
        in ["FUNDAMENTAL_STRENGTH", "EARNINGS_STRENGTH"]
        and get_direction(item) == "POSITIVE"
    ]

    positive_dividends = [
        item for item in observations
        if get_observation_type(item)
        in ["DIVIDEND_STRENGTH", "DIVIDEND_CHANGE"]
        and get_direction(item) == "POSITIVE"
    ]

    if not negative_price or not positive_fundamentals:
        return None

    matched = [
        max(negative_price, key=lambda item: item.get("importance", 5)),
        max(positive_fundamentals, key=lambda item: item.get("importance", 5)),
    ]

    if positive_dividends:
        matched.append(
            max(positive_dividends, key=lambda item: item.get("importance", 5))
        )

    return {
        "signal_type": "POTENTIAL_VALUE_DISLOCATION",
        "title": "Potential valuation dislocation",
        "description": (
            "The subject shows negative price movement while fundamental "
            "indicators remain positive. This may indicate a disconnect "
            "between market pricing and underlying business performance."
        ),
        "observations": matched,
        "pattern_bonus": 1 if positive_dividends else 0,
    }


# ---------------------------------------------------------
# SUPPLY GAP DETECTOR
# ---------------------------------------------------------

def detect_supply_gap(observations):
    demand_increase = [
        item for item in observations
        if get_observation_type(item) in ["DEMAND_CHANGE", "DEMAND_SURGE"]
        and get_direction(item) == "POSITIVE"
    ]

    supply_constraint = [
        item for item in observations
        if get_observation_type(item) in ["SUPPLY_CHANGE", "SUPPLY_CONSTRAINT"]
        and get_direction(item) == "NEGATIVE"
    ]

    if not demand_increase or not supply_constraint:
        return None

    matched = [
        max(demand_increase, key=lambda item: item.get("importance", 5)),
        max(supply_constraint, key=lambda item: item.get("importance", 5)),
    ]

    return {
        "signal_type": "SUPPLY_GAP",
        "title": "Potential supply gap",
        "description": (
            "Demand appears to be increasing while supply is constrained. "
            "This combination may create a market gap worth investigating."
        ),
        "observations": matched,
        "pattern_bonus": 1,
    }


# ---------------------------------------------------------
# PRICE ARBITRAGE DETECTOR
# ---------------------------------------------------------

def detect_price_arbitrage(observations):
    external_price = [
        item for item in observations
        if get_observation_type(item) in ["GLOBAL_PRICE", "EXTERNAL_PRICE"]
        and get_direction(item) == "NEGATIVE"
    ]

    local_price = [
        item for item in observations
        if get_observation_type(item) in ["LOCAL_PRICE", "PRICE_LEVEL"]
        and str(item.get("geography", "")).upper() == "TANZANIA"
    ]

    if not external_price or not local_price:
        return None

    matched = [
        max(external_price, key=lambda item: item.get("importance", 5)),
        max(local_price, key=lambda item: item.get("importance", 5)),
    ]

    return {
        "signal_type": "POTENTIAL_PRICE_ARBITRAGE",
        "title": "Potential price arbitrage",
        "description": (
            "External pricing appears weaker while the Tanzanian market "
            "remains comparatively elevated. This may create a price "
            "differential worth investigating after transport, taxes, "
            "currency and transaction costs."
        ),
        "observations": matched,
        "pattern_bonus": 1,
    }


# ---------------------------------------------------------
# TECHNOLOGY OPPORTUNITY DETECTOR
# ---------------------------------------------------------

def detect_technology_opportunity(observations):
    technology_improvement = [
        item for item in observations
        if get_observation_type(item) in [
            "TECHNOLOGY_CHANGE",
            "CAPABILITY_CHANGE",
            "TECHNOLOGY_IMPROVEMENT",
        ]
        and get_direction(item) == "POSITIVE"
    ]

    cost_reduction = [
        item for item in observations
        if get_observation_type(item) in ["COST_CHANGE", "PRICE_CHANGE"]
        and get_direction(item) == "NEGATIVE"
    ]

    adoption_increase = [
        item for item in observations
        if get_observation_type(item) in [
            "ADOPTION_CHANGE",
            "DEMAND_CHANGE",
            "DEMAND_SURGE",
        ]
        and get_direction(item) == "POSITIVE"
    ]

    if not technology_improvement or not (cost_reduction or adoption_increase):
        return None

    matched = [
        max(technology_improvement, key=lambda item: item.get("importance", 5))
    ]

    if cost_reduction:
        matched.append(
            max(cost_reduction, key=lambda item: item.get("importance", 5))
        )

    if adoption_increase:
        matched.append(
            max(adoption_increase, key=lambda item: item.get("importance", 5))
        )

    return {
        "signal_type": "TECHNOLOGY_OPPORTUNITY",
        "title": "Emerging technology opportunity",
        "description": (
            "Technology capability is improving alongside falling costs "
            "and/or increasing adoption. This combination may create new "
            "business or automation opportunities."
        ),
        "observations": matched,
        "pattern_bonus": 1,
    }


# ---------------------------------------------------------
# CONVERGENCE DETECTOR
# ---------------------------------------------------------

def detect_convergence(observations):
    if len(observations) < 3:
        return None

    sources = {
        get_source(item)
        for item in observations
        if get_source(item)
    }

    if len(sources) < 2:
        return None

    directions = {
        get_direction(item)
        for item in observations
        if get_direction(item) != "NEUTRAL"
    }

    if len(directions) != 1:
        return None

    return {
        "signal_type": "CONVERGING_SIGNAL",
        "title": "Converging evidence detected",
        "description": (
            "Multiple observations from independent sources are pointing "
            "in the same direction. This increases the importance of "
            "investigating the underlying trend."
        ),
        "observations": observations,
        "pattern_bonus": 1,
    }


# ---------------------------------------------------------
# BUILD SIGNAL
# ---------------------------------------------------------

def build_signal(pattern, all_observations):
    observations = pattern["observations"]

    evidence_quality = calculate_evidence_quality(observations)
    source_diversity = calculate_source_diversity(observations)
    persistence = calculate_persistence(observations)

    strength = calculate_signal_strength(
        evidence_quality,
        source_diversity,
        persistence,
        pattern.get("pattern_bonus", 0),
    )

    confidence = calculate_signal_confidence(
        evidence_quality,
        source_diversity,
    )

    subject = observations[0].get("subject", "Unknown")

    geography = next(
        (
            item.get("geography")
            for item in observations
            if item.get("geography")
        ),
        "GLOBAL",
    )

    observation_ids = [
        item.get("id")
        for item in observations
        if item.get("id") is not None
    ]

    title = pattern["title"]
    if subject:
        title = f"{title}: {subject}"

    return {
        "signal_type": pattern["signal_type"],
        "title": title,
        "description": pattern["description"],
        "subject": subject,
        "domain": observations[0].get("domain", "GENERAL"),
        "geography": geography,
        "observation_ids": observation_ids,
        "strength": strength,
        "confidence": confidence,
        "evidence_quality": evidence_quality,
        "source_diversity": source_diversity,
        "persistence": persistence,
        "status": "DETECTED",
        "detected_at": utc_now(),
        "engine_version": SIGNAL_ENGINE_VERSION,
    }


# ---------------------------------------------------------
# SIGNAL IDENTITY
# ---------------------------------------------------------

def signal_key(signal):
    return (
        signal.get("signal_type"),
        signal.get("subject"),
        tuple(sorted(signal.get("observation_ids", []))),
    )


# ---------------------------------------------------------
# UPGRADE / MIGRATE EXISTING SIGNALS
# ---------------------------------------------------------

def upgrade_existing_signals(signals, research):
    research_by_id = {
        item.get("id"): item
        for item in research
        if item.get("id") is not None
    }

    changed = False

    for signal in signals:
        observation_ids = signal.get("observation_ids", [])

        observations = [
            research_by_id[item_id]
            for item_id in observation_ids
            if item_id in research_by_id
        ]

        if not observations:
            continue

        evidence_quality = calculate_evidence_quality(observations)
        source_diversity = calculate_source_diversity(observations)
        persistence = calculate_persistence(observations)

        new_values = {
            "evidence_quality": evidence_quality,
            "source_diversity": source_diversity,
            "persistence": persistence,
            "strength": calculate_signal_strength(
                evidence_quality,
                source_diversity,
                persistence,
            ),
            "confidence": calculate_signal_confidence(
                evidence_quality,
                source_diversity,
            ),
            "engine_version": SIGNAL_ENGINE_VERSION,
        }

        for field, value in new_values.items():
            if signal.get(field) != value:
                signal[field] = value
                changed = True

    return changed


# ---------------------------------------------------------
# DETECT NEW SIGNALS
# ---------------------------------------------------------

def detect_signals():
    research = load_research()
    existing_signals = load_signals()
    detected_signals = []

    if not research:
        return detected_signals

    subjects = {}

    for observation in research:
        subject = observation.get("subject")
        if subject:
            subjects.setdefault(subject, []).append(observation)

    existing_keys = {
        signal_key(signal) for signal in existing_signals
    }
    detected_keys = set()

    for observations in subjects.values():
        patterns = [
            detect_value_dislocation(observations),
            detect_supply_gap(observations),
            detect_price_arbitrage(observations),
            detect_technology_opportunity(observations),
            detect_convergence(observations),
        ]

        for pattern in patterns:
            if not pattern:
                continue

            signal = build_signal(pattern, observations)
            key = signal_key(signal)

            if key in existing_keys or key in detected_keys:
                continue

            detected_signals.append(signal)
            detected_keys.add(key)

    return detected_signals


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@app.get("/")
def dashboard(request: Request):
    projects = load_projects()
    opportunities = load_opportunities()
    research = load_research()
    research_reports = load_research_reports()
    research_feeds = build_research_feeds()
    signals = load_signals()
    research_tasks = load_research_tasks()
    research_findings = load_research_findings()
    research_executions = load_research_executions()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": "malume",
            "projects": projects,
            "opportunities": opportunities,
            "research": research,
            "research_reports": research_reports,
            "research_feeds": research_feeds,
            "signals": signals,
            "research_tasks": research_tasks,
            "research_findings": research_findings,
            "research_executions": research_executions,
            "project_count": len(projects),
            "opportunity_count": len(opportunities),
            "research_count": len(research),
            "research_report_count": len(research_reports),
            "signal_count": len(signals),
            "research_task_count": len(research_tasks),
            "research_finding_count": len(research_findings),
            "research_execution_count": len(research_executions),
        },
    )


# ---------------------------------------------------------
# CREATE PROJECT
# ---------------------------------------------------------

@app.post("/projects/create")
def create_project(
    name: str = Form(...),
    description: str = Form(""),
    technology: str = Form(""),
):
    projects = load_projects()

    project = {
        "id": max(
            (item.get("id", 0) for item in projects),
            default=0,
        ) + 1,
        "name": name,
        "description": description,
        "technology": technology,
        "status": "ACTIVE",
    }

    projects.append(project)
    save_projects(projects)

    return RedirectResponse(url="/", status_code=303)


# ---------------------------------------------------------
# DELETE PROJECT
# ---------------------------------------------------------

@app.post("/projects/{project_id}/delete")
def delete_project(project_id: int):
    projects = [
        item for item in load_projects()
        if item.get("id") != project_id
    ]

    save_projects(projects)

    return RedirectResponse(url="/", status_code=303)


# ---------------------------------------------------------
# RESEARCH / OBSERVATION INGESTION
# ---------------------------------------------------------

def create_research_observation(record: ResearchRecord):
    research = load_research()

    next_id = max(
        (item.get("id", 0) for item in research),
        default=0,
    ) + 1

    record_data = record.model_dump()
    record_data["id"] = next_id
    record_data["timestamp"] = utc_now()

    research.append(record_data)
    save_research(research)

    return record_data


@app.post("/api/research")
def add_research(record: ResearchRecord):
    record_data = create_research_observation(record)

    return {
        "message": "Research observation added successfully",
        "observation": record_data,
    }


@app.post("/api/research/observations")
def add_research_observation(record: ResearchRecord):
    record_data = create_research_observation(record)

    return {
        "message": "Research observation added successfully",
        "observation": record_data,
    }


@app.get("/api/research/observations")
def get_research_observations():
    return {"observations": load_research()}


# ---------------------------------------------------------
# RAW RESEARCH REPORT INGESTION
# ---------------------------------------------------------

@app.post("/api/research/reports")
def add_research_report(report: ResearchReport):
    reports = load_research_reports()

    report_data = report.model_dump()
    report_data["id"] = max(
        (item.get("id", 0) for item in reports),
        default=0,
    ) + 1
    report_data["received_at"] = utc_now()

    reports.append(report_data)
    save_research_reports(reports)

    return {
        "message": "Research report added successfully",
        "report": report_data,
    }


# ---------------------------------------------------------
# RESEARCH FEED REGISTRATION API
# ---------------------------------------------------------

@app.post("/api/research/feeds")
def add_research_feed(feed: ResearchFeed):
    feeds = load_research_feeds()

    existing_feed = next(
        (item for item in feeds if item.get("name") == feed.name),
        None,
    )

    if existing_feed:
        return {
            "message": "Research feed already exists",
            "feed": existing_feed,
        }

    feed_data = feed.model_dump()
    feed_data["id"] = max(
        (item.get("id", 0) for item in feeds),
        default=0,
    ) + 1
    feed_data["created_at"] = utc_now()

    feeds.append(feed_data)
    save_research_feeds(feeds)

    return {
        "message": "Research feed added successfully",
        "feed": feed_data,
    }


@app.get("/api/research/feeds")
def get_research_feeds():
    return {"feeds": build_research_feeds()}


# ---------------------------------------------------------
# SIGNAL DETECTION API
# ---------------------------------------------------------

@app.post("/api/signals/detect")
def run_signal_detection():
    signals = load_signals()
    research = load_research()

    signals_changed = upgrade_existing_signals(signals, research)
    detected_signals = detect_signals()

    next_id = max(
        (item.get("id", 0) for item in signals),
        default=0,
    ) + 1

    for signal in detected_signals:
        signal["id"] = next_id
        signals.append(signal)
        next_id += 1

    save_signals(signals)

    return {
        "message": "Signal detection completed",
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "upgraded_existing_signals": signals_changed,
        "new_signals": detected_signals,
        "total_signals": len(signals),
    }


@app.post("/api/signals/migrate")
def migrate_signals():
    signals = load_signals()
    research = load_research()

    signals_changed = upgrade_existing_signals(signals, research)
    save_signals(signals)

    return {
        "message": "Signal migration completed",
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "changed": signals_changed,
        "total_signals": len(signals),
        "signals": signals,
    }


@app.get("/api/signals")
def get_signals():
    return {
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "signals": load_signals(),
    }


# ---------------------------------------------------------
# OPPORTUNITY ENGINE
# ---------------------------------------------------------

@app.post("/api/opportunities/generate")
def run_opportunity_generation():
    signals = load_signals()
    research = load_research()
    opportunities = load_opportunities()

    result = generate_opportunities_from_signals(
        signals=signals,
        research=research,
        existing_opportunities=opportunities,
    )

    save_opportunities(opportunities)

    return {
        "message": "Opportunity generation completed",
        "opportunity_engine_version": OPPORTUNITY_ENGINE_VERSION,
        **result,
    }


@app.get("/api/opportunities")
def get_opportunities():
    opportunities = sorted(
        load_opportunities(),
        key=lambda item: item.get("priority_score", 0),
        reverse=True,
    )

    return {
        "opportunity_engine_version": OPPORTUNITY_ENGINE_VERSION,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities,
    }


# ---------------------------------------------------------
# RESEARCH TASK ENGINE
# ---------------------------------------------------------

@app.post("/api/research-tasks/generate")
def run_research_task_generation():
    opportunities = load_opportunities()
    tasks = load_research_tasks()

    result = generate_research_tasks(
        opportunities=opportunities,
        existing_tasks=tasks,
    )

    save_research_tasks(tasks)

    return {
        "message": "Research task generation completed",
        **result,
    }


@app.get("/api/research-tasks")
def get_research_tasks():
    tasks = load_research_tasks()

    status_order = {
        "OPEN": 0,
        "IN_PROGRESS": 1,
        "BLOCKED": 2,
        "COMPLETED": 3,
        "CANCELLED": 4,
    }

    ranked_tasks = sorted(
        tasks,
        key=lambda task: (
            status_order.get(
                str(task.get("status", "OPEN")).upper(),
                5,
            ),
            task.get("created_at", ""),
        ),
    )

    return {
        "research_task_engine_version": RESEARCH_TASK_ENGINE_VERSION,
        "total_tasks": len(ranked_tasks),
        "tasks": ranked_tasks,
    }


# ---------------------------------------------------------
# RESEARCH EXECUTION ENGINE
# ---------------------------------------------------------

def execute_task_by_key(task_key: str):
    """
    Execute one saved research task, persist the execution,
    and deduplicate findings across repeated searches.
    """

    tasks = load_research_tasks()

    task = next(
        (
            item for item in tasks
            if str(item.get("task_key", "")) == task_key
        ),
        None,
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Research task not found: {task_key}",
        )

    started_at = utc_now()
    execution_id = max(
        (
            item.get("id", 0)
            for item in load_research_executions()
        ),
        default=0,
    ) + 1

    task["status"] = "IN_PROGRESS"
    task["updated_at"] = started_at
    save_research_tasks(tasks)

    try:
        result = execute_research_task(task)
    except Exception as exc:
        # Never return environment variables or API-key values.
        result = {
            "status": "FAILED",
            "error": f"{type(exc).__name__}: research execution failed",
            "findings": [],
            "provider": "TAVILY",
            "caveats": [
                "Inspect the server terminal for diagnostic details.",
            ],
        }

    result_status = str(result.get("status", "FAILED")).upper()
    raw_findings = result.get("findings") or []
    if not isinstance(raw_findings, list):
        raw_findings = []

    findings = load_research_findings()
    executions = load_research_executions()

    existing_keys = {
        str(item.get("finding_key") or item.get("url") or "").strip()
        for item in findings
    }

    new_findings = []
    duplicate_count = 0
    next_finding_id = max(
        (item.get("id", 0) for item in findings),
        default=0,
    ) + 1

    completed_at = utc_now()

    for raw_finding in raw_findings:
        if not isinstance(raw_finding, dict):
            continue

        finding = dict(raw_finding)
        finding_key = str(
            finding.get("finding_key")
            or finding.get("url")
            or (
                str(finding.get("domain", ""))
                + "|"
                + str(finding.get("title", ""))
            )
        ).strip()

        if not finding_key:
            continue

        if finding_key in existing_keys:
            duplicate_count += 1
            continue

        finding["id"] = next_finding_id
        finding["finding_key"] = finding_key
        finding["execution_id"] = execution_id
        finding["task_key"] = task_key
        finding["opportunity_key"] = task.get("opportunity_key")
        finding["review_status"] = "UNVERIFIED"
        finding["saved_at"] = completed_at

        findings.append(finding)
        new_findings.append(finding)
        existing_keys.add(finding_key)
        next_finding_id += 1

    save_research_findings(findings)

    execution = {
        "id": execution_id,
        "task_key": task_key,
        "opportunity_key": task.get("opportunity_key"),
        "subject": task.get("subject"),
        "provider": result.get("provider", "TAVILY"),
        "status": result_status,
        "query": result.get("query"),
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_seconds": result.get("duration_seconds"),
        "result_count": len(raw_findings),
        "new_findings_count": len(new_findings),
        "duplicate_findings_count": duplicate_count,
        "error": result.get("error"),
        "caveats": result.get("caveats") or [],
        "engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
    }

    executions.append(execution)
    save_research_executions(executions)

    # Record attempt history without pretending that a failed search
    # has answered the underlying research question.
    task["attempt_count"] = int(task.get("attempt_count", 0)) + 1
    task["last_attempt_at"] = started_at
    task["last_execution_id"] = execution_id
    task["last_execution_status"] = result_status
    task["last_execution_findings_count"] = len(raw_findings)
    task["last_execution_error"] = result.get("error")
    task["updated_at"] = completed_at

    if result_status == "BLOCKED_CONFIGURATION":
        task["status"] = "BLOCKED"
    elif result_status == "COMPLETED" and raw_findings:
        task["status"] = "COMPLETED"
    elif result_status == "COMPLETED":
        # A completed search with no usable results can be retried.
        task["status"] = "OPEN"
    else:
        task["status"] = "OPEN"

    save_research_tasks(tasks)

    return {
        "message": "Research task execution finished",
        "execution": execution,
        "new_findings": new_findings,
        "new_findings_count": len(new_findings),
        "duplicate_findings_count": duplicate_count,
        "task": task,
    }


@app.post("/api/research-tasks/{task_key}/execute")
def execute_research_task_endpoint(task_key: str):
    """Execute a specific task by its stable task_key."""
    return execute_task_by_key(task_key)


@app.post("/api/research-tasks/execute-next")
def execute_next_research_task():
    """
    Execute the oldest OPEN task.
    Retry BLOCKED tasks only when no OPEN tasks remain.
    """

    tasks = load_research_tasks()

    open_tasks = sorted(
        [
            task for task in tasks
            if str(task.get("status", "OPEN")).upper() == "OPEN"
        ],
        key=lambda task: task.get("created_at", ""),
    )

    blocked_tasks = sorted(
        [
            task for task in tasks
            if str(task.get("status", "")).upper() == "BLOCKED"
        ],
        key=lambda task: task.get("created_at", ""),
    )

    candidates = open_tasks or blocked_tasks

    if not candidates:
        return {
            "message": "No OPEN or BLOCKED research tasks are available.",
            "executed": False,
            "total_tasks": len(tasks),
        }

    task_key = candidates[0].get("task_key")

    if not task_key:
        raise HTTPException(
            status_code=400,
            detail="Selected research task has no task_key.",
        )

    result = execute_task_by_key(str(task_key))
    result["executed"] = True

    return result


# ---------------------------------------------------------
# RETRIEVE SAVED FINDINGS AND EXECUTIONS
# ---------------------------------------------------------

@app.get("/api/research-findings")
def get_research_findings(
    task_key: str | None = None,
    opportunity_key: str | None = None,
    review_status: str | None = None,
):
    findings = load_research_findings()

    if task_key:
        findings = [
            item for item in findings
            if item.get("task_key") == task_key
        ]

    if opportunity_key:
        findings = [
            item for item in findings
            if item.get("opportunity_key") == opportunity_key
        ]

    if review_status:
        findings = [
            item for item in findings
            if str(item.get("review_status", "")).upper()
            == review_status.upper()
        ]

    return {
        "total_findings": len(findings),
        "findings": findings,
        "note": (
            "Saved web findings are unverified until independently reviewed."
        ),
    }


@app.get("/api/research-executions")
def get_research_executions(
    task_key: str | None = None,
    limit: int = 50,
):
    executions = load_research_executions()

    if task_key:
        executions = [
            item for item in executions
            if item.get("task_key") == task_key
        ]

    executions = sorted(
        executions,
        key=lambda item: item.get("completed_at", ""),
        reverse=True,
    )

    limit = max(1, min(limit, 200))
    executions = executions[:limit]

    return {
        "research_execution_engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
        "total_returned": len(executions),
        "executions": executions,
    }


# ---------------------------------------------------------
# RUNTIME SYSTEM STATUS
# ---------------------------------------------------------

@app.get("/api/system/status")
def system_status():
    return {
        "application": "MY TECH LAB",
        "signal_engine_version": SIGNAL_ENGINE_VERSION,
        "opportunity_engine_version": OPPORTUNITY_ENGINE_VERSION,
        "research_task_engine_version": RESEARCH_TASK_ENGINE_VERSION,
        "research_execution_engine_version": RESEARCH_EXECUTION_ENGINE_VERSION,
        "main_module": __file__,
        "signal_count": len(load_signals()),
        "opportunity_count": len(load_opportunities()),
        "research_count": len(load_research()),
        "research_report_count": len(load_research_reports()),
        "research_feed_count": len(load_research_feeds()),
        "research_task_count": len(load_research_tasks()),
        "research_execution_count": len(load_research_executions()),
        "research_finding_count": len(load_research_findings()),
        "status": "ONLINE",
    }
