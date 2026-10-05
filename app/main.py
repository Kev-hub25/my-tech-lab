from pathlib import Path
import json

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

PROJECTS_FILE = BASE_DIR / "projects.json"

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
# PROJECT DATA
# ---------------------------------------------------------

def load_projects():
    if not PROJECTS_FILE.exists():
        return []

    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return []


def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as file:
        json.dump(projects, file, indent=4)


# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

@app.get("/")
def dashboard(request: Request):

    projects = load_projects()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": "malume",
            "projects": projects,
            "project_count": len(projects),
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