from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import Attrezzatura

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TIPI = ["pentola", "fermentatore", "pompa", "chiller", "filtro", "dosatore",
        "misuratore", "imbottigliatrice", "fusto", "capsulatrice", "altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/attrezzature", response_class=HTMLResponse)
def lista(request: Request, db: Session = Depends(get_db)):
    items = db.query(Attrezzatura).order_by(Attrezzatura.nome).all()
    return templates.TemplateResponse(request, "attrezzature.html", {
        "attrezzature": items, "tipi": TIPI, "session": request.session,
    })


@router.post("/attrezzature/nuova")
def nuova(
    request: Request,
    nome: str = Form(...),
    tipo: str = Form("altro"),
    marca: str = Form(""),
    modello: str = Form(""),
    numero_seriale: str = Form(""),
    capacita_litri: float = Form(None),
    ubicazione: str = Form(""),
    data_acquisto: str = Form(None),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(Attrezzatura(
        nome=nome, tipo=tipo,
        marca=marca or None, modello=modello or None,
        numero_seriale=numero_seriale or None,
        capacita_litri=capacita_litri,
        ubicazione=ubicazione or None,
        data_acquisto=data_acquisto,
        note=note or None,
    ))
    db.commit()
    return RedirectResponse("/attrezzature", status_code=303)


@router.post("/attrezzature/{aid}/elimina")
def elimina(aid: int, db: Session = Depends(get_db)):
    a = db.query(Attrezzatura).filter(Attrezzatura.id == aid).first()
    if a:
        db.delete(a)
        db.commit()
    return RedirectResponse("/attrezzature", status_code=303)


@router.post("/attrezzature/{aid}/manutenzione")
def manutenzione(aid: int, data: str = Form(...), db: Session = Depends(get_db)):
    a = db.query(Attrezzatura).filter(Attrezzatura.id == aid).first()
    if a:
        a.ultima_manutenzione = data
        db.commit()
    return RedirectResponse("/attrezzature", status_code=303)
