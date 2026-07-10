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
    acquirente: str = Form(""),
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
        acquirente=acquirente.strip() or None,
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


@router.get("/acquisti/report/spese", response_class=HTMLResponse)
def report_spese(request: Request, db: Session = Depends(get_db)):
    ordini = db.query(OrdineAcquisto).order_by(OrdineAcquisto.data.desc()).all()
    per_persona = {}
    for o in ordini:
        chi = (o.acquirente or "Non specificato").strip() or "Non specificato"
        tot = sum((r.quantita or 0) * (r.prezzo_unitario or 0) for r in o.righe) if o.righe else (o.totale or 0)
        entry = per_persona.setdefault(chi, {"totale": 0.0, "ordini": []})
        entry["totale"] += tot
        entry["ordini"].append({"ordine": o, "totale": round(tot, 2)})

    per_persona = dict(sorted(per_persona.items(), key=lambda kv: kv[1]["totale"], reverse=True))
    for v in per_persona.values():
        v["totale"] = round(v["totale"], 2)

    totale_generale = round(sum(v["totale"] for v in per_persona.values()), 2)

    return templates.TemplateResponse(request, "acquisti_report_spese.html", {
        "per_persona": per_persona,
        "totale_generale": totale_generale,
        "session": request.session,
    })


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


@router.post("/acquisti/{oid}/acquirente")
def aggiorna_acquirente(oid: int, acquirente: str = Form(""), db: Session = Depends(get_db)):
    ordine = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if ordine:
        ordine.acquirente = acquirente.strip() or None
        db.commit()
    return RedirectResponse(f"/acquisti/{oid}?msg=Acquirente+aggiornato", status_code=303)


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


@router.get("/acquisti/{oid}/conferma-review", response_class=HTMLResponse)
def conferma_review(oid: int, request: Request, db: Session = Depends(get_db)):
    """Mostra una tabella di revisione: righe già presenti in magazzino (aggiornamento quantità)
    e righe nuove (con campi editabili prima della creazione definitiva dell'articolo)."""
    ordine = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if not ordine or ordine.stato == "ricevuto":
        return RedirectResponse(f"/acquisti/{oid}", status_code=303)

    righe_info = []
    for r in ordine.righe:
        existing = db.query(InventarioItem).filter(
            InventarioItem.nome.ilike(f"%{r.nome[:25]}%")
        ).first()
        righe_info.append({
            "riga": r,
            "existing": existing,
        })

    return templates.TemplateResponse(request, "acquisti_conferma_review.html", {
        "ordine": ordine,
        "righe_info": righe_info,
        "categorie": ["consumabile", "non_consumabile", "ingrediente", "chimico", "packaging"],
        "unita": UNITA,
        "session": request.session,
    })


@router.post("/acquisti/{oid}/conferma")
def conferma_ordine(
    oid: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Segna ordine come 'ricevuto' e aggiunge tutto al magazzino, usando eventuali
    correzioni fatte nella pagina di revisione (nome/categoria/unità/soglia per riga nuova)."""
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


@router.post("/acquisti/{oid}/conferma-review")
async def conferma_ordine_review(oid: int, request: Request, db: Session = Depends(get_db)):
    """Conferma l'ordine applicando le correzioni fatte sui nuovi articoli nella pagina di revisione."""
    ordine = db.query(OrdineAcquisto).filter(OrdineAcquisto.id == oid).first()
    if not ordine or ordine.stato == "ricevuto":
        return RedirectResponse(f"/acquisti/{oid}", status_code=303)

    form = await request.form()

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
            nome_edit = (form.get(f"nome_{r.id}") or r.nome).strip() or r.nome
            categoria_edit = form.get(f"categoria_{r.id}") or r.categoria or "consumabile"
            if categoria_edit not in ["consumabile", "non_consumabile", "ingrediente", "chimico", "packaging"]:
                categoria_edit = "consumabile"
            unita_edit = form.get(f"unita_{r.id}") or r.unita or "pz"
            try:
                soglia_edit = float(form.get(f"soglia_{r.id}") or 0)
            except ValueError:
                soglia_edit = 0
            db.add(InventarioItem(
                nome=nome_edit,
                categoria=categoria_edit,
                unita=unita_edit,
                quantita=r.quantita or 0,
                quantita_minima=soglia_edit,
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
