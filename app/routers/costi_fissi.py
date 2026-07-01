"""Gestione costi fissi del birrificio per calcolo breakeven."""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import CostoFisso

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIE = ["energia", "affitto", "personale", "attrezzatura", "manutenzione", "assicurazione", "software", "altro"]
PERIODICITA = ["mensile", "annuale", "per_cotta"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/costi-fissi", response_class=HTMLResponse)
def lista_costi(request: Request, db: Session = Depends(get_db)):
    costi = db.query(CostoFisso).order_by(CostoFisso.categoria, CostoFisso.id).all()
    # Calcola mensile equivalente per tutti
    def mensile(c):
        if c.periodicita == "annuale":
            return (c.importo or 0) / 12
        if c.periodicita == "per_cotta":
            return (c.importo or 0) * 4  # assume 4 cotte/mese
        return c.importo or 0

    totale_mensile = sum(mensile(c) for c in costi if c.attivo)
    totale_annuale = totale_mensile * 12

    cat_totali = {}
    for c in costi:
        if c.attivo:
            cat_totali[c.categoria] = cat_totali.get(c.categoria, 0) + mensile(c)

    return templates.TemplateResponse(request, "costi_fissi.html", {
        "costi": costi,
        "categorie": CATEGORIE,
        "periodicita_opts": PERIODICITA,
        "totale_mensile": round(totale_mensile, 2),
        "totale_annuale": round(totale_annuale, 2),
        "cat_totali": {k: round(v, 2) for k, v in cat_totali.items()},
        "session": request.session,
    })


@router.post("/costi-fissi/nuovo")
async def nuovo_costo(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    db.add(CostoFisso(
        categoria=form.get("categoria", "altro"),
        descrizione=form.get("descrizione", "").strip(),
        importo=float(form.get("importo", "0").replace(",", ".") or 0),
        periodicita=form.get("periodicita", "mensile"),
        attivo=True,
        note=form.get("note", "").strip() or None,
    ))
    db.commit()
    return RedirectResponse("/costi-fissi", status_code=303)


@router.post("/costi-fissi/{cid}/toggle")
def toggle_costo(cid: int, db: Session = Depends(get_db)):
    c = db.query(CostoFisso).filter(CostoFisso.id == cid).first()
    if c:
        c.attivo = not c.attivo
        db.commit()
    return RedirectResponse("/costi-fissi", status_code=303)


@router.post("/costi-fissi/{cid}/elimina")
def elimina_costo(cid: int, db: Session = Depends(get_db)):
    c = db.query(CostoFisso).filter(CostoFisso.id == cid).first()
    if c:
        db.delete(c)
        db.commit()
    return RedirectResponse("/costi-fissi", status_code=303)


@router.get("/api/costi-fissi/summary")
def costi_summary(db: Session = Depends(get_db)):
    costi = db.query(CostoFisso).filter(CostoFisso.attivo == True).all()
    def mensile(c):
        if c.periodicita == "annuale":
            return (c.importo or 0) / 12
        if c.periodicita == "per_cotta":
            return (c.importo or 0) * 4
        return c.importo or 0
    totale = sum(mensile(c) for c in costi)
    return {"totale_mensile": round(totale, 2), "totale_annuale": round(totale * 12, 2)}
