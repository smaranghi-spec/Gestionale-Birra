from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from ..db import SessionLocal
from ..models import IngredienteRicetta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class QuickUpdatePayload(BaseModel):
    quantita: float
    unita: str
    time_min: Optional[int] = None
    note: Optional[str] = None


@router.get("/ingredienti/{ing_id}/modifica", response_class=HTMLResponse)
def form_modifica(ing_id: int, request: Request, db: Session = Depends(get_db)):
    ing = db.query(IngredienteRicetta).filter(IngredienteRicetta.id == ing_id).first()
    if not ing:
        return HTMLResponse("Ingrediente non trovato", status_code=404)
    return templates.TemplateResponse(request, "modifica_ingrediente.html", {"ing": ing})


@router.post("/ingredienti/{ing_id}/modifica")
def salva_modifica(
    ing_id: int,
    nome: str = Form(...),
    categoria: str = Form(...),
    quantita: float = Form(...),
    unita: str = Form(...),
    time_min: int = Form(None),
    note: str = Form(None),
    fermentable_type: str = Form(None),
    yield_percent: float = Form(None),
    color_srm: float = Form(None),
    alpha_acid: float = Form(None),
    hop_use: str = Form(None),
    hop_form: str = Form(None),
    attenuation: float = Form(None),
    yeast_type: str = Form(None),
    yeast_form: str = Form(None),
    misc_type: str = Form(None),
    misc_use: str = Form(None),
    db: Session = Depends(get_db),
):
    ing = db.query(IngredienteRicetta).filter(IngredienteRicetta.id == ing_id).first()
    if not ing:
        return RedirectResponse("/ricette/html", status_code=303)

    ing.nome = nome
    ing.categoria = categoria
    ing.quantita = quantita
    ing.unita = unita
    ing.time_min = time_min
    ing.note = note or None
    ing.fermentable_type = fermentable_type or None
    ing.yield_percent = yield_percent
    ing.color_srm = color_srm
    ing.alpha_acid = alpha_acid
    ing.hop_use = hop_use or None
    ing.hop_form = hop_form or None
    ing.attenuation = attenuation
    ing.yeast_type = yeast_type or None
    ing.yeast_form = yeast_form or None
    ing.misc_type = misc_type or None
    ing.misc_use = misc_use or None
    db.commit()

    return RedirectResponse(f"/ricette/{ing.ricetta_id}", status_code=303)


@router.post("/ingredienti/{ing_id}/elimina")
def elimina_ingrediente(ing_id: int, db: Session = Depends(get_db)):
    ing = db.query(IngredienteRicetta).filter(IngredienteRicetta.id == ing_id).first()
    if ing:
        ricetta_id = ing.ricetta_id
        db.delete(ing)
        db.commit()
        return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)
    return RedirectResponse("/ricette/html", status_code=303)


@router.post("/ingredienti/{ing_id}/quick-update")
def quick_update(ing_id: int, payload: QuickUpdatePayload, db: Session = Depends(get_db)):
    ing = db.query(IngredienteRicetta).filter(IngredienteRicetta.id == ing_id).first()
    if not ing:
        return {"error": "not found"}, 404
    ing.quantita = payload.quantita
    ing.unita = payload.unita
    ing.time_min = payload.time_min
    ing.note = payload.note
    db.commit()
    return {"ok": True}
