from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .db import Base, engine
from .models import User, Attrezzatura, Ricetta

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR.parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

app = FastAPI(title="Gestionale Birrificio")

Base.metadata.create_all(bind=engine)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "title": "Dashboard"})
