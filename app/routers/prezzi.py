import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PrezzoCache

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("prezzi")

CATEGORIE_RICERCA = ["ingrediente", "attrezzatura", "accessorio", "luppolo", "malto", "lievito", "chimico"]
FORNITORI_DISPONIBILI = ["Pinta", "Polsinelli", "Enosystem", "Beer and Wine", "MrMalt"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _get_ultime_query(db: Session) -> list:
    """Recupera le ultime ricerche uniche in modo sicuro compatibile con PostgreSQL e SQLite."""
    try:
        recenti = db.query(PrezzoCache.query).order_by(PrezzoCache.id.desc()).limit(50).all()
        visti = set()
        ultime = []
        for r in recenti:
            q = r[0] if isinstance(r, (tuple, list)) else getattr(r, "query", str(r))
            if q and str(q).strip() and q not in visti:
                visti.add(q)
                ultime.append(q)
                if len(ultime) >= 10:
                    break
        return ultime
    except Exception as e:
        logger.warning(f"Errore recupero ultime query prezzo: {e}")
        db.rollback()
        return []


def _salva_cache(db: Session, query: str, risultati: list):
    try:
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
    except Exception as e:
        db.rollback()
        logger.warning(f"Impossibile salvare cache prezzi: {e}")


def _leggi_cache(db: Session, query: str) -> list:
    try:
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
    except Exception as e:
        logger.warning(f"Errore lettura cache prezzi: {e}")
        db.rollback()
        return []


@router.get("/prezzi", response_class=HTMLResponse)
def pagina_prezzi(request: Request, db: Session = Depends(get_db)):
    ultime_query = _get_ultime_query(db)
    return templates.TemplateResponse(request, "prezzi.html", {
        "request": request,
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

    query_full = q
    risultati = None
    da_cache = False

    if not aggiorna:
        cached = _leggi_cache(db, query_full)
        if cached:
            risultati = cached
            da_cache = True

    if not da_cache:
        try:
            risultati = await cerca_prezzi(query_full)
            _salva_cache(db, query_full, risultati)
        except Exception as e:
            logger.error(f"Errore scraping prezzi per '{query_full}': {e}")
            db.rollback()
            risultati = []

    ultime_query = _get_ultime_query(db)

    return templates.TemplateResponse(request, "prezzi.html", {
        "request": request,
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
    query_full = q
    risultati = await cerca_prezzi(query_full)
    _salva_cache(db, query_full, risultati)
    return JSONResponse({"query": query_full, "risultati": risultati})
