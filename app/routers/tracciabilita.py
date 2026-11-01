"""
Report tracciabilità bidirezionale:
1. Da Materia Prima / Lotto Fornitore -> a Cotte e Bottiglie prodotte (se un lotto è difettoso, quali lotti birra sono a rischio?)
2. Da Cotta / Batch -> a tutti i lotti specifici di materie prime consumati (audit di qualità, certificazione alimentare)
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db import SessionLocal
from ..models import IngredienteRicetta, Ricetta, Cotta, InventarioItem, CottaIngredienteLotto

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
    cerca_term = cerca.strip()

    # 1. Tracciabilità Lotti Fornitore -> Cotte (CottaIngredienteLotto)
    q_lotti = db.query(CottaIngredienteLotto).order_by(CottaIngredienteLotto.timestamp.desc(), CottaIngredienteLotto.id.desc())
    if cerca_term:
        q_lotti = q_lotti.filter(
            (CottaIngredienteLotto.numero_lotto.ilike(f"%{cerca_term}%")) |
            (CottaIngredienteLotto.codice_ingrediente.ilike(f"%{cerca_term}%")) |
            (CottaIngredienteLotto.nome_ingrediente.ilike(f"%{cerca_term}%")) |
            (CottaIngredienteLotto.fornitore.ilike(f"%{cerca_term}%"))
        )
    registrazioni_lotti = q_lotti.all()

    # Raggruppa per lotto fornitore
    lotti_gruppi = {}
    for r in registrazioni_lotti:
        key = (r.numero_lotto or "Senza Lotto", r.codice_ingrediente or "—", r.nome_ingrediente, r.fornitore or "—")
        if key not in lotti_gruppi:
            inv_collegato = db.query(InventarioItem).filter(InventarioItem.id == r.inventario_id).first() if r.inventario_id else None
            lotti_gruppi[key] = {
                "numero_lotto": r.numero_lotto,
                "codice_ingrediente": r.codice_ingrediente,
                "nome_ingrediente": r.nome_ingrediente,
                "categoria": r.categoria,
                "fornitore": r.fornitore,
                "data_scadenza": r.data_scadenza,
                "totale_usato": 0.0,
                "unita": r.unita,
                "cotte": [],
                "inventario": inv_collegato,
            }
        lotti_gruppi[key]["totale_usato"] = round(lotti_gruppi[key]["totale_usato"] + (r.quantita_usata or 0.0), 3)
        if r.cotta and r.cotta not in lotti_gruppi[key]["cotte"]:
            lotti_gruppi[key]["cotte"].append(r.cotta)

    lotti_list = list(lotti_gruppi.values())

    # 2. Tracciabilità Cotte -> Lotti (Cotte con ingredienti_lotti)
    q_cotte = db.query(Cotta).order_by(Cotta.id.desc())
    if cerca_term:
        q_cotte = q_cotte.filter(
            (Cotta.codice.ilike(f"%{cerca_term}%")) |
            (Cotta.nome.ilike(f"%{cerca_term}%"))
        )
    cotte_list = q_cotte.limit(30).all()

    # 3. Report storico ricette-ingredienti per consultazione classica
    q_ing = db.query(IngredienteRicetta.nome, func.count(IngredienteRicetta.id).label("n_uses"))\
        .group_by(IngredienteRicetta.nome)\
        .order_by(IngredienteRicetta.nome)
    if cerca_term:
        q_ing = q_ing.filter(IngredienteRicetta.nome.ilike(f"%{cerca_term}%"))
    ingredienti_usati = q_ing.all()

    report_ricette = []
    for nome_ing, n_uses in ingredienti_usati[:25]:
        righe = db.query(IngredienteRicetta).filter(IngredienteRicetta.nome == nome_ing).all()
        ricetta_ids = list({r.ricetta_id for r in righe})
        ricette = db.query(Ricetta).filter(Ricetta.id.in_(ricetta_ids)).all()
        inv = db.query(InventarioItem).filter(InventarioItem.nome.ilike(f"%{nome_ing[:25]}%")).first()
        report_ricette.append({
            "nome": nome_ing,
            "sku": righe[0].codice_ingrediente if righe and righe[0].codice_ingrediente else (inv.codice_ingrediente if inv else None),
            "n_uses": n_uses,
            "ricette": ricette,
            "inventario": inv,
        })

    return templates.TemplateResponse(request, "tracciabilita.html", {
        "cerca": cerca,
        "lotti_tracciati": lotti_list,
        "cotte_tracciate": cotte_list,
        "report": report_ricette,
        "n_lotti": len(lotti_list),
        "n_cotte": len(cotte_list),
        "n_ingredienti": len(report_ricette),
        "session": request.session,
    })
