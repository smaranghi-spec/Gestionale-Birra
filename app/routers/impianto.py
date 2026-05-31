"""
Gestione profilo impianto birrificio (es. BrewMonk B50).
Calcola volumi, efficienza e parametri di cotta basati sul profilo selezionato.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import ProfiloBirrificio

router = APIRouter()
templates = Jinja2Templates(directory="templates")

BREWMONK_B50 = {
    "nome": "BrewMonk B50",
    "marca": "BrewMonk",
    "modello": "B50",
    "vol_batch_litri": 50.0,
    "vol_preboil_litri": 57.0,
    "vol_mash_litri": 67.0,
    "dead_space_litri": 3.5,
    "perdita_bollitura_pct": 7.0,
    "efficienza_default": 72.0,
    "durata_bollitura_min": 60,
    "note": (
        "BrewMonk B50 — Sistema all-in-one da 50L. "
        "Vol. mash: 67L (1.3 L/kg per 10 kg grist), Pre-boil: 57L, "
        "Post-boil target: 50L. Dead space 3.5L totale. "
        "Efficienza tipica 68-75%."
    ),
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/impianto", response_class=HTMLResponse)
def lista(request: Request, msg: str = None, db: Session = Depends(get_db)):
    profili = db.query(ProfiloBirrificio).order_by(ProfiloBirrificio.nome).all()
    principale = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.is_principale == True).first()
    return templates.TemplateResponse(request, "impianto.html", {
        "profili": profili,
        "principale": principale,
        "msg": msg,
        "session": request.session,
    })


@router.post("/impianto/nuovo")
def nuovo_profilo(
    nome: str = Form(...),
    marca: str = Form(""),
    modello: str = Form(""),
    vol_batch_litri: float = Form(50.0),
    vol_preboil_litri: float = Form(57.0),
    vol_mash_litri: float = Form(67.0),
    dead_space_litri: float = Form(3.5),
    perdita_bollitura_pct: float = Form(7.0),
    efficienza_default: float = Form(72.0),
    durata_bollitura_min: int = Form(60),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    p = ProfiloBirrificio(
        nome=nome, marca=marca or None, modello=modello or None,
        vol_batch_litri=vol_batch_litri, vol_preboil_litri=vol_preboil_litri,
        vol_mash_litri=vol_mash_litri, dead_space_litri=dead_space_litri,
        perdita_bollitura_pct=perdita_bollitura_pct,
        efficienza_default=efficienza_default,
        durata_bollitura_min=durata_bollitura_min,
        note=note or None,
    )
    db.add(p)
    db.commit()
    return RedirectResponse("/impianto?msg=Profilo+aggiunto", status_code=303)


@router.post("/impianto/preset-b50")
def preset_b50(db: Session = Depends(get_db)):
    existing = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.modello == "B50").first()
    if existing:
        return RedirectResponse("/impianto?msg=BrewMonk+B50+già+presente", status_code=303)
    p = ProfiloBirrificio(**BREWMONK_B50)
    db.add(p)
    db.commit()
    return RedirectResponse("/impianto?msg=BrewMonk+B50+aggiunto", status_code=303)


@router.post("/impianto/{pid}/imposta-principale")
def imposta_principale(pid: int, db: Session = Depends(get_db)):
    db.query(ProfiloBirrificio).update({"is_principale": False})
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if p:
        p.is_principale = True
    db.commit()
    return RedirectResponse("/impianto?msg=Impianto+principale+aggiornato", status_code=303)


@router.post("/impianto/{pid}/elimina")
def elimina(pid: int, db: Session = Depends(get_db)):
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/impianto?msg=Profilo+eliminato", status_code=303)


@router.get("/impianto/{pid}/calcola")
def calcola(pid: int, vol_batch: float = 20.0, db: Session = Depends(get_db)):
    """API JSON: dato un volume batch target, calcola tutti i volumi."""
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if not p:
        return JSONResponse({"errore": "Profilo non trovato"}, status_code=404)
    ratio = vol_batch / (p.vol_batch_litri or 50.0)
    return JSONResponse({
        "vol_batch": round(vol_batch, 1),
        "vol_preboil": round(p.vol_preboil_litri * ratio, 1),
        "vol_mash": round(p.vol_mash_litri * ratio, 1),
        "dead_space": round(p.dead_space_litri, 1),
        "perdita_bollitura_pct": p.perdita_bollitura_pct,
        "efficienza": p.efficienza_default,
        "durata_bollitura_min": p.durata_bollitura_min,
    })
