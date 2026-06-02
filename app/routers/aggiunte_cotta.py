"""Aggiunte fuori ricetta durante la cotta (infusi, puree, spezie, frutta…)."""
from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import AggiuntaCotta

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/cotte/{cotta_id}/aggiunte")
def aggiungi(
    cotta_id: int,
    nome: str = Form(...),
    tipo: str = Form("infuso"),
    quantita: str = Form(""),
    unita: str = Form("g"),
    fase: str = Form("fermentazione"),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(AggiuntaCotta(
        cotta_id=cotta_id,
        nome=nome,
        tipo=tipo,
        quantita=float(quantita) if quantita.strip() else None,
        unita=unita,
        fase=fase,
        note=note or None,
    ))
    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}#aggiunte", status_code=303)


@router.post("/cotte/{cotta_id}/aggiunte/{aid}/elimina")
def elimina(cotta_id: int, aid: int, db: Session = Depends(get_db)):
    a = db.query(AggiuntaCotta).filter(
        AggiuntaCotta.id == aid, AggiuntaCotta.cotta_id == cotta_id
    ).first()
    if a:
        db.delete(a)
        db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}#aggiunte", status_code=303)
