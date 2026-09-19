from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..db import SessionLocal
from ..models import Cotta, Ricetta, InventarioItem, Vendita

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/dashboard", response_class=HTMLResponse)
def view_dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
        
    # Calcolo dati per i grafici
    oggi = datetime.now()
    sei_mesi_fa = (oggi - timedelta(days=180)).strftime("%Y-%m-%d")

    # 1. Vendite per Mese (Ultimi 6 mesi)
    vendite = db.query(Vendita).filter(Vendita.data >= sei_mesi_fa, Vendita.stato == "confermata").all()
    vendite_per_mese = {}
    for v in vendite:
        mese = v.data[:7]  # YYYY-MM
        if mese not in vendite_per_mese:
            vendite_per_mese[mese] = 0.0
        if v.prezzo_euro:
            vendite_per_mese[mese] += v.prezzo_euro
            
    # Ordina per mese
    mesi_ordinati = sorted(list(vendite_per_mese.keys()))
    chart_vendite = {
        "labels": mesi_ordinati,
        "data": [vendite_per_mese[m] for m in mesi_ordinati]
    }

    # 2. Stili più prodotti
    cotte = db.query(Cotta).filter(Cotta.stato != "pianificata").all()
    stili_count = {}
    for c in cotte:
        if c.ricetta_id:
            r = db.query(Ricetta).filter(Ricetta.id == c.ricetta_id).first()
            if r and r.stile:
                stili_count[r.stile] = stili_count.get(r.stile, 0) + 1
    
    stili_labels = list(stili_count.keys())
    stili_data = list(stili_count.values())

    # 3. Valore dell'inventario
    inv = db.query(InventarioItem).all()
    valore_totale = 0.0
    for item in inv:
        if item.quantita and item.prezzo_unitario:
            valore_totale += item.quantita * item.prezzo_unitario

    return templates.TemplateResponse(request, "dashboard.html", {
        "session": request.session,
        "chart_vendite": chart_vendite,
        "chart_stili": {"labels": stili_labels, "data": stili_data},
        "valore_inventario": valore_totale,
        "totale_cotte": len(cotte)
    })
