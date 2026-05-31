"""
Report tracciabilità ingredienti:
- Per ogni ingrediente: quali ricette lo usano, quali cotte lo hanno impiegato.
- Permette di rispondere a "se questo lotto di malto era difettoso, quali batch sono a rischio?"
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import SessionLocal
from ..models import IngredienteRicetta, Ricetta, Cotta, InventarioItem

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/tracciabilita", response_class=HTMLResponse)
def tracciabilita(request: Request, cerca: str = "", db: Session = Depends(get_db)):
    """
    Per ogni nome ingrediente usato in almeno una ricetta:
    mostra le ricette collegate e le cotte da quelle ricette.
    """
    q = db.query(IngredienteRicetta.nome, func.count(IngredienteRicetta.id).label("n_uses"))\
        .group_by(IngredienteRicetta.nome)\
        .order_by(IngredienteRicetta.nome)

    if cerca.strip():
        q = q.filter(IngredienteRicetta.nome.ilike(f"%{cerca.strip()}%"))

    ingredienti_usati = q.all()

    report = []
    for nome_ing, n_uses in ingredienti_usati:
        righe = db.query(IngredienteRicetta)\
            .filter(IngredienteRicetta.nome == nome_ing)\
            .all()

        ricetta_ids = list({r.ricetta_id for r in righe})
        ricette = db.query(Ricetta).filter(Ricetta.id.in_(ricetta_ids)).all()

        cotte = db.query(Cotta)\
            .filter(Cotta.ricetta_id.in_(ricetta_ids))\
            .order_by(Cotta.id.desc())\
            .limit(10).all()

        inv = db.query(InventarioItem)\
            .filter(InventarioItem.nome.ilike(f"%{nome_ing[:25]}%"))\
            .first()

        report.append({
            "nome": nome_ing,
            "n_uses": n_uses,
            "ricette": ricette,
            "cotte": cotte,
            "inventario": inv,
        })

    return templates.TemplateResponse(request, "tracciabilita.html", {
        "report": report,
        "cerca": cerca,
        "n_ingredienti": len(report),
        "session": request.session,
    })
