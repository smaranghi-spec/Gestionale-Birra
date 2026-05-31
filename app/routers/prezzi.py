import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/prezzi", response_class=HTMLResponse)
def pagina_prezzi(request: Request):
    return templates.TemplateResponse(request, "prezzi.html", {
        "query": "",
        "risultati": None,
    })


@router.get("/prezzi/cerca", response_class=HTMLResponse)
async def cerca(request: Request, q: str = ""):
    from ..scrapers import cerca_prezzi
    risultati = []
    if q.strip():
        risultati = await cerca_prezzi(q.strip())
    return templates.TemplateResponse(request, "prezzi.html", {
        "query": q,
        "risultati": risultati,
    })
