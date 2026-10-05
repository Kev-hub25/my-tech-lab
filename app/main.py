from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# Location of this file: app/main.py
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

# HTML templates
templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

# Static files: CSS, JavaScript, images
app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )