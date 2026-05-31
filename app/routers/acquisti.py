"""
Gestione ordini di acquisto con flusso:
  bozza → conferma articoli (modifica se errati) → ricevuto → aggiunta automatica magazzino
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import OrdineAcquisto, RigaOrdine, InventarioItem

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIE = ["ingrediente", "consumabile", "attrezzatura", "accessorio", "packaging", "chimico", "altro"]
UNITA = ["kg", "g", "L", "mL", "pz", "rotolo", "busta", "flacone", "altro"]
FORNITORI_SUGGERITI = ["MrMalt", "Polsinelli", "Beer and Wine", "Pinta", "AEB Group", "Altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/acquisti", response_class=HTMLResponse)
def lista_ordini(request: Request, msg: str = None, db: Session = Depends(get_db)):
    ordini = db.query(OrdineAcquisto).order_by(OrdineAcquisto.id.desc()).all()
    return templates.TemplateResponse(request, "acquisti_lista.html", {
        "ordini": ordini,
        "msg": msg,
        "session": request.session,
    })


@router.get("/acquisti/nuovo", response_class=HTMLResponse)
def nuovo_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "acquisti_nuovo.html", {
        "categorie": CATEGORIE,
        "unita": UNITA,
        "fornitori": FORNITORI_SUGGERITI,
        "session": request.session,
    })


@router.post("/acquisti/crea")
def crea_ordine(
    request: Request,
    fornitore: str = Form(""),
    data: str = Form(""),
    note: str = Form(""),
    righe_json: str = Form("[]"),
    db: Session = Depends(get_db),
):
    try:
        righe_data = json.loads(righe_json)
    except Exception:
        righe_data = []

    if not data:
        data = datetime.now().strftime("%Y-%m-%d")

    ordine = OrdineAcquisto(
        fornitore=fornitore or None,
        data=data,
        note=note or None,
        stato="bozza",
    )
    db.add(ordine)
    db.flush()

    totale = 0.0
    for r in righe_data:
        nome = (r.get("nome") or "").strip()
        if not nome:
            continue
        qty = float(r.get("quantita") or 1)
        pu = float(r.get("prezzo_unitario") or 0)
        totale += qty * pu
        db.add(RigaOrdine(
            ordine_id=ordine.id,
            nome=nome,
            categoria=r.get("categoria") or "ingrediente",
            quantita=qty,
            unita=r.get("unita") or "pz",
            prezzo_unitario=pu if pu > 0 else None,
            note=r.get("note") or None,
        ))

    ordine.totale = round(totale, 2)
    db.commit()
    return RedirectResponse(f"/acquisti/{ordine.id}", status_code=303)


@router.get("/acquisti/{oid}", response_class=HTMLResponse)
def dettaglio_ordine(oid: int, request: Request, msg: str = None, db: Session = Depends(get_db)):
    ordine = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if not ordine:
        return RedirectResponse("/acquisti", status_code=303)
    totale = sum((r.quantita or 0) * (r.prezzo_unitario or 0) for r in ordine.righe)
    return templates.TemplateResponse(request, "acquisti_dettaglio.html", {
        "ordine": ordine,
        "totale": round(totale, 2),
        "categorie": CATEGORIE,
        "unita": UNITA,
        "msg": msg,
        "session": request.session,
    })


@router.post("/acquisti/{oid}/aggiorna-riga/{rid}")
def aggiorna_riga(
    oid: int, rid: int,
    nome: str = Form(...),
    categoria: str = Form("ingrediente"),
    quantita: float = Form(1.0),
    unita: str = Form("pz"),
    prezzo_unitario: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    r = db.query(RigaOrdine).filter(RigaOrdine.id == rid, RigaOrdine.ordine_id == oid).first()
    if r:
        r.nome = nome
        r.categoria = categoria
        r.quantita = quantita
        r.unita = unita
        r.prezzo_unitario = float(prezzo_unitario) if prezzo_unitario.strip() else None
        r.note = note or None
        _ricalcola_totale(oid, db)
        db.commit()
    return RedirectResponse(f"/acquisti/{oid}?msg=Riga+aggiornata", status_code=303)


@router.post("/acquisti/{oid}/elimina-riga/{rid}")
def elimina_riga(oid: int, rid: int, db: Session = Depends(get_db)):
    r = db.query(RigaOrdine).filter(RigaOrdine.id == rid, RigaOrdine.ordine_id == oid).first()
    if r:
        db.delete(r)
        _ricalcola_totale(oid, db)
        db.commit()
    return RedirectResponse(f"/acquisti/{oid}", status_code=303)


@router.post("/acquisti/{oid}/aggiungi-riga")
def aggiungi_riga(
    oid: int,
    nome: str = Form(...),
    categoria: str = Form("ingrediente"),
    quantita: float = Form(1.0),
    unita: str = Form("pz"),
    prezzo_unitario: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    ordine = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if ordine and ordine.stato == "bozza":
        db.add(RigaOrdine(
            ordine_id=oid, nome=nome, categoria=categoria,
            quantita=quantita, unita=unita,
            prezzo_unitario=float(prezzo_unitario) if prezzo_unitario.strip() else None,
            note=note or None,
        ))
        _ricalcola_totale(oid, db)
        db.commit()
    return RedirectResponse(f"/acquisti/{oid}?msg=Riga+aggiunta", status_code=303)


@router.post("/acquisti/{oid}/conferma")
def conferma_ordine(oid: int, db: Session = Depends(get_db)):
    """Segna ordine come 'ricevuto' e aggiunge tutto al magazzino."""
    ordine = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if not ordine or ordine.stato == "ricevuto":
        return RedirectResponse(f"/acquisti/{oid}", status_code=303)

    for r in ordine.righe:
        existing = db.query(InventarioItem).filter(
            InventarioItem.nome.ilike(f"%{r.nome[:25]}%")
        ).first()
        if existing:
            existing.quantita = (existing.quantita or 0) + (r.quantita or 0)
            existing.ultimo_aggiornamento = datetime.now().strftime("%Y-%m-%d %H:%M")
            if ordine.fornitore and not existing.fornitore:
                existing.fornitore = ordine.fornitore
            if r.prezzo_unitario and not existing.prezzo_unitario:
                existing.prezzo_unitario = r.prezzo_unitario
        else:
            cat = r.categoria if r.categoria in ["consumabile", "non_consumabile", "ingrediente", "chimico", "packaging"] else "consumabile"
            db.add(InventarioItem(
                nome=r.nome,
                categoria=cat,
                unita=r.unita or "pz",
                quantita=r.quantita or 0,
                quantita_minima=0,
                prezzo_unitario=r.prezzo_unitario,
                fornitore=ordine.fornitore or None,
                ultimo_aggiornamento=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ))

    ordine.stato = "ricevuto"
    db.commit()
    return RedirectResponse(f"/acquisti/{oid}?msg=Ordine+ricevuto+e+magazzino+aggiornato", status_code=303)


@router.post("/acquisti/{oid}/elimina")
def elimina_ordine(oid: int, db: Session = Depends(get_db)):
    o = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if o:
        db.delete(o)
        db.commit()
    return RedirectResponse("/acquisti?msg=Ordine+eliminato", status_code=303)


def _ricalcola_totale(oid: int, db: Session):
    righe = db.query(RigaOrdine).filter(RigaOrdine.ordine_id == oid).all()
    totale = sum((r.quantita or 0) * (r.prezzo_unitario or 0) for r in righe)
    o = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if o:
        o.totale = round(totale, 2)
