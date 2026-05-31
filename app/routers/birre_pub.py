from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Ricetta, Stile

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/birre", response_class=HTMLResponse)
def birre_pubbliche(request: Request, db: Session = Depends(get_db)):
    birre = db.query(Ricetta).filter(Ricetta.pubblica == True).order_by(Ricetta.nome).all()
    return templates.TemplateResponse(request, "birre_pub.html", {
        "birre": birre,
        "session": {},
    })


@router.get("/birre/{rid}", response_class=HTMLResponse)
def birra_dettaglio(rid: int, request: Request, db: Session = Depends(get_db)):
    birra = db.query(Ricetta).filter(Ricetta.id == rid, Ricetta.pubblica == True).first()
    if not birra:
        return HTMLResponse("<h1>Birra non trovata</h1>", status_code=404)
    stile = db.query(Stile).filter(Stile.id == birra.stile_id).first() if birra.stile_id else None
    return templates.TemplateResponse(request, "birra_dettaglio_pub.html", {
        "birra": birra,
        "stile": stile,
        "ingredienti": birra.ingredienti,
        "session": {},
    })
