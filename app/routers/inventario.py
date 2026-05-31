from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import SessionLocal
from ..models import InventarioItem

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIE = ["consumabile", "non_consumabile", "ingrediente", "chimico", "packaging"]
UNITA = ["kg", "g", "L", "mL", "pz", "rotolo", "busta", "flacone", "altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/inventario", response_class=HTMLResponse)
def lista(request: Request, db: Session = Depends(get_db)):
    items = db.query(InventarioItem).order_by(InventarioItem.categoria, InventarioItem.nome).all()
    sotto_soglia = [i for i in items if i.quantita_minima and i.quantita <= i.quantita_minima]
    return templates.TemplateResponse(request, "inventario.html", {
        "items": items,
        "sotto_soglia": sotto_soglia,
        "categorie": CATEGORIE,
        "unita": UNITA,
        "session": request.session,
    })


@router.post("/inventario/nuovo")
def nuovo(
    nome: str = Form(...),
    categoria: str = Form("consumabile"),
    unita: str = Form("pz"),
    quantita: float = Form(0),
    quantita_minima: float = Form(0),
    prezzo_unitario: float = Form(None),
    fornitore: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(InventarioItem(
        nome=nome, categoria=categoria, unita=unita,
        quantita=quantita, quantita_minima=quantita_minima,
        prezzo_unitario=prezzo_unitario,
        fornitore=fornitore or None,
        note=note or None,
        ultimo_aggiornamento=datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))
    db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/{iid}/aggiorna")
def aggiorna_quantita(
    iid: int,
    delta: float = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
    if item:
        item.quantita = max(0.0, (item.quantita or 0) + delta)
        item.ultimo_aggiornamento = datetime.now().strftime("%Y-%m-%d %H:%M")
        if note:
            item.note = (item.note or "") + f"\n[{datetime.now().strftime('%d/%m/%y')}] {delta:+.2f} {item.unita}: {note}"
        db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/{iid}/elimina")
def elimina(iid: int, db: Session = Depends(get_db)):
    item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/inventario", status_code=303)
