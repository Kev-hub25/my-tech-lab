from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


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

app = FastAPI(title="MY TECH LAB")


templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)


app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
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

    data: dict[str, Any] = Field(
        default_factory=dict
    )

    evidence_url: str | None = None

    source_report: str | None = None

    confidence: int = Field(
        default=5,
        ge=1,
        le=10
    )

    importance: int = Field(
        default=5,
        ge=1,
        le=10
    )


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

    observation_ids: list[int] = Field(
        default_factory=list
    )

    strength: int = Field(
        default=5,
        ge=1,
        le=10
    )

    confidence: int = Field(
        default=5,
        ge=1,
        le=10
    )

    evidence_quality: int = Field(
        default=5,
        ge=1,
        le=10
    )

    source_diversity: int = Field(
        default=1,
        ge=1,
        le=10
    )

    persistence: int = Field(
        default=1,
        ge=1,
        le=10
    )

    status: str = "DETECTED"


# ---------------------------------------------------------
# PROJECT DATA
# ---------------------------------------------------------

def load_projects():

    if not PROJECTS_FILE.exists():
        return []

    try:

        with open(
            PROJECTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_projects(projects):

    with open(
        PROJECTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            projects,
            file,
            indent=4
        )


# ---------------------------------------------------------
# OPPORTUNITY DATA
# ---------------------------------------------------------

def load_opportunities():

    if not OPPORTUNITIES_FILE.exists():
        return []

    try:

        with open(
            OPPORTUNITIES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_opportunities(opportunities):

    with open(
        OPPORTUNITIES_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            opportunities,
            file,
            indent=4
        )


# ---------------------------------------------------------
# RESEARCH DATA
# ---------------------------------------------------------

def load_research():

    if not RESEARCH_FILE.exists():
        return []

    try:

        with open(
            RESEARCH_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_research(research):

    with open(
        RESEARCH_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            research,
            file,
            indent=4
        )


# ---------------------------------------------------------
# RAW RESEARCH REPORT DATA
# ---------------------------------------------------------

def load_research_reports():

    if not RESEARCH_REPORTS_FILE.exists():
        return []

    try:

        with open(
            RESEARCH_REPORTS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_research_reports(reports):

    with open(
        RESEARCH_REPORTS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            reports,
            file,
            indent=4
        )


# ---------------------------------------------------------
# RESEARCH FEED DATA
# ---------------------------------------------------------

def load_research_feeds():

    if not RESEARCH_FEEDS_FILE.exists():
        return []

    try:

        with open(
            RESEARCH_FEEDS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_research_feeds(feeds):

    with open(
        RESEARCH_FEEDS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            feeds,
            file,
            indent=4
        )


def build_research_feeds():

    feeds = load_research_feeds()

    reports = load_research_reports()

    research = load_research()

    enriched_feeds = []

    for feed in feeds:

        feed_name = feed["name"]

        feed_reports = [
            report
            for report in reports
            if report.get("feed") == feed_name
        ]

        feed_observations = [
            record
            for record in research
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

        latest_update = (
            max(timestamps)
            if timestamps
            else None
        )

        enriched_feed = dict(feed)

        enriched_feed["report_count"] = len(
            feed_reports
        )

        enriched_feed["observation_count"] = len(
            feed_observations
        )

        enriched_feed["last_updated"] = latest_update

        enriched_feeds.append(
            enriched_feed
        )

    return enriched_feeds


# ---------------------------------------------------------
# SIGNAL DATA
# ---------------------------------------------------------

def load_signals():

    if not SIGNALS_FILE.exists():
        return []

    try:

        with open(
            SIGNALS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (json.JSONDecodeError, OSError):

        return []


def save_signals(signals):

    with open(
        SIGNALS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            signals,
            file,
            indent=4
        )


# ---------------------------------------------------------
# SIGNAL ENGINE V2
# ---------------------------------------------------------

def get_observation_type(observation):

    return str(
        observation.get(
            "observation_type",
            "GENERAL"
        )
    ).upper()


def get_direction(observation):

    return str(
        observation.get(
            "direction",
            "NEUTRAL"
        )
    ).upper()


def get_source(observation):

    return str(
        observation.get(
            "source",
            ""
        )
    ).strip().upper()


def calculate_evidence_quality(observations):

    if not observations:
        return 1

    scores = []

    for observation in observations:

        confidence = int(
            observation.get(
                "confidence",
                5
            )
        )

        importance = int(
            observation.get(
                "importance",
                5
            )
        )

        score = (
            confidence +
            importance
        ) / 2

        if observation.get("data"):
            score += 1

        if (
            observation.get("evidence_url")
            or observation.get("source_report")
        ):
            score += 1

        score = min(
            score,
            10
        )

        scores.append(score)

    return max(
        1,
        min(
            10,
            round(
                sum(scores) /
                len(scores)
            )
        )
    )


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

    observation_count = len(
        observations
    )

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
    pattern_bonus=0
):

    score = (
        evidence_quality * 0.50
        +
        source_diversity * 0.25
        +
        persistence * 0.25
        +
        pattern_bonus
    )

    return max(
        1,
        min(
            10,
            round(score)
        )
    )


def calculate_signal_confidence(
    evidence_quality,
    source_diversity
):

    score = (
        evidence_quality * 0.60
        +
        source_diversity * 0.40
    )

    return max(
        1,
        min(
            10,
            round(score)
        )
    )


def detect_value_dislocation(observations):

    negative_price = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            == "PRICE_CHANGE"
            and
            get_direction(observation)
            == "NEGATIVE"
        )
    ]

    positive_fundamentals = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "FUNDAMENTAL_STRENGTH",
                "EARNINGS_STRENGTH"
            ]
            and
            get_direction(observation)
            == "POSITIVE"
        )
    ]

    positive_dividends = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "DIVIDEND_STRENGTH",
                "DIVIDEND_CHANGE"
            ]
            and
            get_direction(observation)
            == "POSITIVE"
        )
    ]

    if not negative_price:
        return None

    if not positive_fundamentals:
        return None

    matched = []

    matched.append(
        max(
            negative_price,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        )
    )

    matched.append(
        max(
            positive_fundamentals,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        )
    )

    if positive_dividends:

        matched.append(
            max(
                positive_dividends,
                key=lambda item:
                    item.get(
                        "importance",
                        5
                    )
            )
        )

    return {
        "signal_type":
            "POTENTIAL_VALUE_DISLOCATION",

        "title":
            "Potential valuation dislocation",

        "description":
            (
                "The subject shows negative price movement "
                "while fundamental indicators remain positive. "
                "This may indicate a disconnect between market "
                "pricing and underlying business performance."
            ),

        "observations":
            matched,

        "pattern_bonus":
            1 if positive_dividends else 0
    }


def detect_supply_gap(observations):

    demand_increase = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "DEMAND_CHANGE",
                "DEMAND_SURGE"
            ]
            and
            get_direction(observation)
            == "POSITIVE"
        )
    ]

    supply_constraint = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "SUPPLY_CHANGE",
                "SUPPLY_CONSTRAINT"
            ]
            and
            get_direction(observation)
            == "NEGATIVE"
        )
    ]

    if not demand_increase:
        return None

    if not supply_constraint:
        return None

    matched = [
        max(
            demand_increase,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        ),
        max(
            supply_constraint,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        )
    ]

    return {
        "signal_type":
            "SUPPLY_GAP",

        "title":
            "Potential supply gap",

        "description":
            (
                "Demand appears to be increasing while supply "
                "is constrained. This combination may create "
                "a market gap worth investigating."
            ),

        "observations":
            matched,

        "pattern_bonus":
            1
    }


def detect_price_arbitrage(observations):

    external_price = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "GLOBAL_PRICE",
                "EXTERNAL_PRICE"
            ]
            and
            get_direction(observation)
            == "NEGATIVE"
        )
    ]

    local_price = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "LOCAL_PRICE",
                "PRICE_LEVEL"
            ]
            and
            str(
                observation.get(
                    "geography",
                    ""
                )
            ).upper()
            == "TANZANIA"
        )
    ]

    if not external_price:
        return None

    if not local_price:
        return None

    matched = [
        max(
            external_price,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        ),
        max(
            local_price,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        )
    ]

    return {
        "signal_type":
            "POTENTIAL_PRICE_ARBITRAGE",

        "title":
            "Potential price arbitrage",

        "description":
            (
                "External pricing appears weaker while the "
                "Tanzanian market remains comparatively elevated. "
                "This may create a price differential worth "
                "investigating after transport, taxes, currency "
                "and transaction costs."
            ),

        "observations":
            matched,

        "pattern_bonus":
            1
    }


def detect_technology_opportunity(observations):

    technology_improvement = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "TECHNOLOGY_CHANGE",
                "CAPABILITY_CHANGE",
                "TECHNOLOGY_IMPROVEMENT"
            ]
            and
            get_direction(observation)
            == "POSITIVE"
        )
    ]

    cost_reduction = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "COST_CHANGE",
                "PRICE_CHANGE"
            ]
            and
            get_direction(observation)
            == "NEGATIVE"
        )
    ]

    adoption_increase = [
        observation
        for observation in observations
        if (
            get_observation_type(observation)
            in [
                "ADOPTION_CHANGE",
                "DEMAND_CHANGE",
                "DEMAND_SURGE"
            ]
            and
            get_direction(observation)
            == "POSITIVE"
        )
    ]

    if not technology_improvement:
        return None

    if (
        not cost_reduction
        and
        not adoption_increase
    ):
        return None

    matched = []

    matched.append(
        max(
            technology_improvement,
            key=lambda item:
                item.get(
                    "importance",
                    5
                )
        )
    )

    if cost_reduction:

        matched.append(
            max(
                cost_reduction,
                key=lambda item:
                    item.get(
                        "importance",
                        5
                    )
            )
        )

    if adoption_increase:

        matched.append(
            max(
                adoption_increase,
                key=lambda item:
                    item.get(
                        "importance",
                        5
                    )
            )
        )

    return {
        "signal_type":
            "TECHNOLOGY_OPPORTUNITY",

        "title":
            "Emerging technology opportunity",

        "description":
            (
                "Technology capability is improving alongside "
                "falling costs and/or increasing adoption. This "
                "combination may create new business or automation "
                "opportunities."
            ),

        "observations":
            matched,

        "pattern_bonus":
            1
    }


def detect_convergence(observations):

    if len(observations) < 3:
        return None

    sources = {
        get_source(observation)
        for observation in observations
        if get_source(observation)
    }

    if len(sources) < 2:
        return None

    directions = {
        get_direction(observation)
        for observation in observations
        if get_direction(observation)
        != "NEUTRAL"
    }

    if len(directions) != 1:
        return None

    return {
        "signal_type":
            "CONVERGING_SIGNAL",

        "title":
            "Converging evidence detected",

        "description":
            (
                "Multiple observations from independent "
                "sources are pointing in the same direction. "
                "This increases the importance of investigating "
                "the underlying trend."
            ),

        "observations":
            observations,

        "pattern_bonus":
            1
    }


def build_signal(
    pattern,
    all_observations
):

    observations = pattern[
        "observations"
    ]

    evidence_quality = (
        calculate_evidence_quality(
            observations
        )
    )

    source_diversity = (
        calculate_source_diversity(
            observations
        )
    )

    persistence = (
        calculate_persistence(
            all_observations
        )
    )

    strength = calculate_signal_strength(
        evidence_quality,
        source_diversity,
        persistence,
        pattern.get(
            "pattern_bonus",
            0
        )
    )

    confidence = calculate_signal_confidence(
        evidence_quality,
        source_diversity
    )

    subject = observations[0].get(
        "subject",
        "Unknown"
    )

    geography = next(
        (
            observation.get(
                "geography"
            )
            for observation in observations
            if observation.get(
                "geography"
            )
        ),
        "GLOBAL"
    )

    observation_ids = [
        observation.get("id")
        for observation in observations
        if observation.get("id")
        is not None
    ]

    title = pattern[
        "title"
    ]

    if subject:

        title = (
            f"{title}: "
            f"{subject}"
        )

    return {
        "signal_type":
            pattern[
                "signal_type"
            ],

        "title":
            title,

        "description":
            pattern[
                "description"
            ],

        "subject":
            subject,

        "domain":
            observations[0].get(
                "domain",
                "GENERAL"
            ),

        "geography":
            geography,

        "observation_ids":
            observation_ids,

        "strength":
            strength,

        "confidence":
            confidence,

        "evidence_quality":
            evidence_quality,

        "source_diversity":
            source_diversity,

        "persistence":
            persistence,

        "status":
            "DETECTED",

        "detected_at":
            datetime.now(
                timezone.utc
            ).isoformat()
    }


def signal_key(signal):

    return (
        signal.get(
            "signal_type"
        ),
        signal.get(
            "subject"
        ),
        tuple(
            sorted(
                signal.get(
                    "observation_ids",
                    []
                )
            )
        )
    )


def upgrade_existing_signals(
    signals,
    research
):

    research_by_id = {
        observation.get("id"):
            observation
        for observation in research
        if observation.get("id")
        is not None
    }

    changed = False

    for signal in signals:

        observation_ids = signal.get(
            "observation_ids",
            []
        )

        observations = [
            research_by_id[
                observation_id
            ]
            for observation_id in observation_ids
            if observation_id
            in research_by_id
        ]

        if not observations:
            continue

        evidence_quality = (
            calculate_evidence_quality(
                observations
            )
        )

        source_diversity = (
            calculate_source_diversity(
                observations
            )
        )

        persistence = (
            calculate_persistence(
                observations
            )
        )

        old_values = (
            signal.get(
                "evidence_quality"
            ),
            signal.get(
                "source_diversity"
            ),
            signal.get(
                "persistence"
            )
        )

        new_values = (
            evidence_quality,
            source_diversity,
            persistence
        )

        if old_values != new_values:

            signal[
                "evidence_quality"
            ] = evidence_quality

            signal[
                "source_diversity"
            ] = source_diversity

            signal[
                "persistence"
            ] = persistence

            signal[
                "strength"
            ] = calculate_signal_strength(
                evidence_quality,
                source_diversity,
                persistence
            )

            signal[
                "confidence"
            ] = calculate_signal_confidence(
                evidence_quality,
                source_diversity
            )

            changed = True

    return changed


def detect_signals():

    research = load_research()

    existing_signals = load_signals()

    detected_signals = []

    if not research:

        return detected_signals


    # -----------------------------------------------------
    # Upgrade signals created by Signal Engine v1.
    # -----------------------------------------------------

    signals_changed = (
        upgrade_existing_signals(
            existing_signals,
            research
        )
    )

    if signals_changed:

        save_signals(
            existing_signals
        )


    # -----------------------------------------------------
    # Group observations by subject.
    # -----------------------------------------------------

    subjects = {}

    for observation in research:

        subject = observation.get(
            "subject"
        )

        if not subject:
            continue

        subjects.setdefault(
            subject,
            []
        ).append(
            observation
        )


    # -----------------------------------------------------
    # Run pattern detectors.
    # -----------------------------------------------------

    for subject, observations in subjects.items():

        patterns = [

            detect_value_dislocation(
                observations
            ),

            detect_supply_gap(
                observations
            ),

            detect_price_arbitrage(
                observations
            ),

            detect_technology_opportunity(
                observations
            ),

            detect_convergence(
                observations
            )
        ]


        for pattern in patterns:

            if not pattern:
                continue


            signal = build_signal(
                pattern,
                observations
            )


            key = signal_key(
                signal
            )


            existing_keys = {
                signal_key(
                    existing
                )
                for existing
                in existing_signals
            }


            detected_keys = {
                signal_key(
                    detected
                )
                for detected
                in detected_signals
            }


            if key in existing_keys:
                continue

            if key in detected_keys:
                continue


            detected_signals.append(
                signal
            )


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

            "project_count":
                len(projects),

            "opportunity_count":
                len(opportunities),

            "research_count":
                len(research),

            "research_report_count":
                len(research_reports),

            "signal_count":
                len(signals),
        }
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
        "id": len(projects) + 1,
        "name": name,
        "description": description,
        "technology": technology,
        "status": "ACTIVE",
    }

    projects.append(project)

    save_projects(projects)

    return RedirectResponse(
        url="/",
        status_code=303
    )


# ---------------------------------------------------------
# DELETE PROJECT
# ---------------------------------------------------------

@app.post("/projects/{project_id}/delete")
def delete_project(project_id: int):

    projects = load_projects()

    projects = [
        project
        for project in projects
        if project["id"] != project_id
    ]

    save_projects(projects)

    return RedirectResponse(
        url="/",
        status_code=303
    )


# ---------------------------------------------------------
# RESEARCH / OBSERVATION INGESTION
# ---------------------------------------------------------

@app.post("/api/research")
def add_research(
    record: ResearchRecord
):

    research = load_research()

    next_id = max(
        [
            item.get(
                "id",
                0
            )
            for item in research
        ],
        default=0
    ) + 1

    record_data = record.model_dump()

    record_data["id"] = next_id

    record_data["timestamp"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    research.append(
        record_data
    )

    save_research(
        research
    )

    return {
        "message":
            "Research observation added successfully",

        "observation":
            record_data
    }


# ---------------------------------------------------------
# RESEARCH OBSERVATION API
# ---------------------------------------------------------

@app.post("/api/research/observations")
def add_research_observation(
    record: ResearchRecord
):

    research = load_research()

    next_id = max(
        [
            item.get(
                "id",
                0
            )
            for item in research
        ],
        default=0
    ) + 1

    record_data = record.model_dump()

    record_data["id"] = next_id

    record_data["timestamp"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    research.append(
        record_data
    )

    save_research(
        research
    )

    return {
        "message":
            "Research observation added successfully",

        "observation":
            record_data
    }


# ---------------------------------------------------------
# GET RESEARCH OBSERVATIONS
# ---------------------------------------------------------

@app.get("/api/research/observations")
def get_research_observations():

    return {
        "observations":
            load_research()
    }


# ---------------------------------------------------------
# RAW RESEARCH REPORT INGESTION
# ---------------------------------------------------------

@app.post("/api/research/reports")
def add_research_report(
    report: ResearchReport
):

    reports = load_research_reports()

    next_id = max(
        [
            item.get(
                "id",
                0
            )
            for item in reports
        ],
        default=0
    ) + 1

    report_data = report.model_dump()

    report_data["id"] = next_id

    report_data["received_at"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    reports.append(
        report_data
    )

    save_research_reports(
        reports
    )

    return {
        "message":
            "Research report added successfully",

        "report":
            report_data
    }


# ---------------------------------------------------------
# RESEARCH FEED REGISTRATION API
# ---------------------------------------------------------

@app.post("/api/research/feeds")
def add_research_feed(
    feed: ResearchFeed
):

    feeds = load_research_feeds()

    existing_feed = next(
        (
            item
            for item in feeds
            if item.get(
                "name"
            ) == feed.name
        ),
        None
    )

    if existing_feed:

        return {
            "message":
                "Research feed already exists",

            "feed":
                existing_feed
        }


    next_id = max(
        [
            item.get(
                "id",
                0
            )
            for item in feeds
        ],
        default=0
    ) + 1


    feed_data = feed.model_dump()

    feed_data["id"] = next_id

    feed_data["created_at"] = (
        datetime.now(
            timezone.utc
        ).isoformat()
    )

    feeds.append(
        feed_data
    )

    save_research_feeds(
        feeds
    )

    return {
        "message":
            "Research feed added successfully",

        "feed":
            feed_data
    }


# ---------------------------------------------------------
# GET RESEARCH FEEDS
# ---------------------------------------------------------

@app.get("/api/research/feeds")
def get_research_feeds():

    return {
        "feeds":
            build_research_feeds()
    }


# ---------------------------------------------------------
# SIGNAL DETECTION API
# ---------------------------------------------------------

@app.post("/api/signals/detect")
def run_signal_detection():

    signals = load_signals()

    detected_signals = detect_signals()


    next_id = max(
        [
            item.get(
                "id",
                0
            )
            for item in signals
        ],
        default=0
    ) + 1


    for signal in detected_signals:

        signal["id"] = next_id

        signals.append(
            signal
        )

        next_id += 1


    save_signals(
        signals
    )


    return {
        "message":
            "Signal detection completed",

        "new_signals":
            detected_signals,

        "total_signals":
            len(signals)
    }


# ---------------------------------------------------------
# GET SIGNALS
# ---------------------------------------------------------

@app.get("/api/signals")
def get_signals():

    return {
        "signals":
            load_signals()
    }