import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PrezzoCache

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIE_RICERCA = ["ingrediente", "attrezzatura", "accessorio", "luppolo", "malto", "lievito", "chimico"]
FORNITORI_DISPONIBILI = ["MrMalt", "Polsinelli", "Beer and Wine", "AEB Group", "Pinta"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _salva_cache(db: Session, query: str, risultati: list):
    db.query(PrezzoCache).filter(PrezzoCache.query == query.lower()).delete()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    for fornitore_data in risultati:
        fornitore = fornitore_data.get("fornitore", "")
        for r in fornitore_data.get("risultati", []):
            if r.get("nome"):
                db.add(PrezzoCache(
                    query=query.lower(),
                    fornitore=fornitore,
                    nome_prodotto=r["nome"][:200],
                    prezzo=r.get("prezzo"),
                    url=r.get("url", "")[:500],
                    aggiornato_il=ts,
                ))
    db.commit()


def _leggi_cache(db: Session, query: str) -> list:
    cached = db.query(PrezzoCache).filter(PrezzoCache.query == query.lower()).all()
    if not cached:
        return []
    by_fornitore = {}
    for c in cached:
        by_fornitore.setdefault(c.fornitore, {"fornitore": c.fornitore, "risultati": [], "aggiornato_il": c.aggiornato_il})
        by_fornitore[c.fornitore]["risultati"].append({
            "nome": c.nome_prodotto,
            "prezzo": c.prezzo,
            "url": c.url,
        })
    return list(by_fornitore.values())


@router.get("/prezzi", response_class=HTMLResponse)
def pagina_prezzi(request: Request, db: Session = Depends(get_db)):
    ultimi = db.query(PrezzoCache.query).distinct().order_by(PrezzoCache.id.desc()).limit(10).all()
    ultime_query = [r[0] for r in ultimi]
    return templates.TemplateResponse(request, "prezzi.html", {
        "query": "",
        "categoria": "",
        "risultati": None,
        "da_cache": False,
        "ultime_query": ultime_query,
        "categorie": CATEGORIE_RICERCA,
        "fornitori_disponibili": FORNITORI_DISPONIBILI,
        "session": request.session,
    })


@router.get("/prezzi/cerca", response_class=HTMLResponse)
async def cerca(
    request: Request,
    q: str = "",
    categoria: str = "",
    aggiorna: bool = False,
    db: Session = Depends(get_db),
):
    from ..scrapers import cerca_prezzi
    q = q.strip()
    if not q:
        return pagina_prezzi(request, db)

    query_full = f"{categoria} {q}".strip() if categoria and categoria not in q else q
    risultati = None
    da_cache = False

    if not aggiorna:
        cached = _leggi_cache(db, query_full)
        if cached:
            risultati = cached
            da_cache = True

    if not da_cache:
        risultati = await cerca_prezzi(query_full)
        _salva_cache(db, query_full, risultati)

    ultimi = db.query(PrezzoCache.query).distinct().order_by(PrezzoCache.id.desc()).limit(10).all()
    ultime_query = [r[0] for r in ultimi]

    return templates.TemplateResponse(request, "prezzi.html", {
        "query": q,
        "categoria": categoria,
        "query_full": query_full,
        "risultati": risultati,
        "da_cache": da_cache,
        "ultime_query": ultime_query,
        "categorie": CATEGORIE_RICERCA,
        "fornitori_disponibili": FORNITORI_DISPONIBILI,
        "session": request.session,
    })


@router.get("/prezzi/cerca-json")
async def cerca_json(q: str = "", categoria: str = "", db: Session = Depends(get_db)):
    from ..scrapers import cerca_prezzi
    q = q.strip()
    if not q:
        return JSONResponse({"errore": "Query vuota", "risultati": []})
    query_full = f"{categoria} {q}".strip() if categoria and categoria not in q else q
    risultati = await cerca_prezzi(query_full)
    _salva_cache(db, query_full, risultati)
    return JSONResponse({"query": query_full, "risultati": risultati})
