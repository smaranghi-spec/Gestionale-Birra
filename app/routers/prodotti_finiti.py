"""Magazzino prodotto finito: bottiglie/fusti da cotte concluse."""
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional

from ..db import SessionLocal
from ..models import ProdottoFinito, Cotta
from ..codici import genera_prossimo_codice_prodotto_finito, genera_codice_lotto_imbottigliamento

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FORMATI = [330, 500, 660, 750, 1000, 1500, 2000, 5000, 10000, 20000, 30000]
TIPI = ["bottiglia", "fusto", "lattina", "bag-in-box"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _gen_codice(cotta: Optional[Cotta], formato_ml: int = None, tipo_pkg: str = None) -> str:
    return genera_codice_lotto_imbottigliamento(cotta, formato_ml, tipo_pkg)


@router.get("/magazzino-finiti", response_class=HTMLResponse)
def lista_finiti(request: Request, db: Session = Depends(get_db)):
    prodotti = db.query(ProdottoFinito).order_by(
        ProdottoFinito.data_imbottigliamento.desc(),
        ProdottoFinito.id.desc()
    ).all()
    cotte = db.query(Cotta).order_by(Cotta.id.desc()).all()

    totale_pezzi = sum(p.n_pezzi_disponibili for p in prodotti)
    valore = sum(
        (p.n_pezzi_disponibili or 0) * (p.prezzo_vendita or 0)
        for p in prodotti
    )
    n_lotti = len(set(p.codice_lotto for p in prodotti if p.codice_lotto))

    return templates.TemplateResponse(request, "magazzino_finiti.html", {
        "prodotti": prodotti,
        "cotte": cotte,
        "formati": FORMATI,
        "tipi": TIPI,
        "totale_pezzi": totale_pezzi,
        "valore_magazzino": round(valore, 2),
        "n_lotti": n_lotti,
        "session": request.session,
    })


@router.post("/magazzino-finiti/nuovo")
async def nuovo_prodotto(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    cotta_id = form.get("cotta_id") or None
    if cotta_id:
        cotta_id = int(cotta_id)
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first() if cotta_id else None

    fmt_ml = int(form.get("formato_ml", 750) or 750)
    pkg = form.get("tipo_packaging", "bottiglia")
    sku = form.get("codice", "").strip() or genera_prossimo_codice_prodotto_finito(db)
    lotto = form.get("codice_lotto", "").strip() or _gen_codice(cotta, fmt_ml, pkg)
    n = int(form.get("n_pezzi", 0) or 0)

    p = ProdottoFinito(
        cotta_id=cotta_id,
        codice=sku,
        nome=form.get("nome", "").strip() or (cotta.nome if cotta else "Birra"),
        codice_lotto=lotto,
        formato_ml=fmt_ml,
        tipo_packaging=pkg,
        n_pezzi_iniziali=n,
        n_pezzi_disponibili=n,
        data_imbottigliamento=form.get("data_imbottigliamento") or datetime.now().strftime("%Y-%m-%d"),
        data_scadenza=form.get("data_scadenza") or None,
        prezzo_vendita=float(form.get("prezzo_vendita", 0).replace(",", ".") or 0) or None,
        note=form.get("note", "").strip() or None,
        stato="disponibile",
    )
    db.add(p)
    db.commit()
    return RedirectResponse("/magazzino-finiti?msg=Lotto+aggiunto", status_code=303)


@router.post("/magazzino-finiti/{pid}/scarica")
async def scarica_pezzi(pid: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    delta = int(form.get("delta", 0) or 0)
    p = db.query(ProdottoFinito).filter(ProdottoFinito.id == pid).first()
    if p:
        p.n_pezzi_disponibili = max(0, (p.n_pezzi_disponibili or 0) - delta)
        if p.n_pezzi_disponibili == 0:
            p.stato = "esaurito"
        db.commit()
    return RedirectResponse("/magazzino-finiti", status_code=303)


@router.post("/magazzino-finiti/{pid}/elimina")
def elimina_prodotto(pid: int, db: Session = Depends(get_db)):
    p = db.query(ProdottoFinito).filter(ProdottoFinito.id == pid).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/magazzino-finiti", status_code=303)


@router.get("/etichetta/{prodotto_id}", response_class=HTMLResponse)
def stampa_etichetta(prodotto_id: int, request: Request, db: Session = Depends(get_db)):
    from ..models import Cotta, Ricetta, IngredienteRicetta
    
    prodotto = db.query(ProdottoFinito).filter(ProdottoFinito.id == prodotto_id).first()
    if not prodotto:
        return RedirectResponse("/magazzino-finiti", status_code=303)
        
    cotta = db.query(Cotta).filter(Cotta.id == prodotto.cotta_id).first() if prodotto.cotta_id else None
    ricetta = db.query(Ricetta).filter(Ricetta.id == cotta.ricetta_id).first() if cotta and cotta.ricetta_id else None
    
    ingredienti = []
    if ricetta:
        aggiunte = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta.id).all()
        # Calcola quantità in grammi per ordinamento corretto (Reg. UE 1169/2011)
        ing_dict = {}
        for a in aggiunte:
            nome = (a.nome or "").strip()
            if not nome:
                continue
            q_gr = float(a.quantita or 0)
            if a.unita == "kg":
                q_gr *= 1000.0
            ing_dict[nome] = ing_dict.get(nome, 0.0) + q_gr
                    
        # Ordina per quantità decrescente (legge europea etichettatura)
        ingredienti_ordinati = sorted(ing_dict.items(), key=lambda x: x[1], reverse=True)
        ingredienti = [i[0] for i in ingredienti_ordinati]
        if "Acqua" not in ingredienti:
            ingredienti.insert(0, "Acqua")
        if not any("lievit" in i.lower() for i in ingredienti):
            ingredienti.append("Lievito")

    return templates.TemplateResponse(request, "etichetta.html", {
        "session": request.session,
        "prodotto": prodotto,
        "cotta": cotta,
        "ricetta": ricetta,
        "ingredienti": ingredienti
    })


@router.get("/cotte/{cotta_id}/imbottiglia", response_class=HTMLResponse)
def form_imbottiglia(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)
    prodotti = db.query(ProdottoFinito).filter(
        ProdottoFinito.cotta_id == cotta_id
    ).order_by(ProdottoFinito.id).all()
    return templates.TemplateResponse(request, "imbottigliamento.html", {
        "cotta": cotta,
        "prodotti": prodotti,
        "formati": FORMATI,
        "tipi": TIPI,
        "codice_suggerito": _gen_codice(cotta, 750, "bottiglia"),
        "oggi": datetime.now().strftime("%Y-%m-%d"),
        "session": request.session,
    })


@router.post("/cotte/{cotta_id}/imbottiglia")
async def salva_imbottigliamento(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)
    form = await request.form()

    formati_ml = form.getlist("formato_ml[]")
    tipi_pkg = form.getlist("tipo_packaging[]")
    n_pezzi_l = form.getlist("n_pezzi[]")
    prezzi_l = form.getlist("prezzo_vendita[]")
    codici_l = form.getlist("codice_lotto[]")
    data_imb = form.get("data_imbottigliamento") or datetime.now().strftime("%Y-%m-%d")
    data_scad = form.get("data_scadenza") or None

    for i, fmt in enumerate(formati_ml):
        n = int(n_pezzi_l[i] if i < len(n_pezzi_l) else 0)
        if n <= 0:
            continue
        try:
            pv = float((prezzi_l[i] if i < len(prezzi_l) else "0").replace(",", ".") or 0) or None
        except Exception:
            pv = None
        pkg = tipi_pkg[i] if i < len(tipi_pkg) else "bottiglia"
        lotto = (codici_l[i] if i < len(codici_l) else "").strip() or _gen_codice(cotta, int(fmt), pkg)
        sku = genera_prossimo_codice_prodotto_finito(db)
        pf_obj = ProdottoFinito(
            cotta_id=cotta_id,
            codice=sku,
            nome=cotta.nome,
            codice_lotto=lotto,
            formato_ml=int(fmt),
            tipo_packaging=pkg,
            n_pezzi_iniziali=n,
            n_pezzi_disponibili=n,
            data_imbottigliamento=data_imb,
            data_scadenza=data_scad,
            prezzo_vendita=pv,
            stato="disponibile",
        )
        db.add(pf_obj)
        db.flush()

    if cotta.stato not in ("condizionamento", "pronta", "archiviata"):
        cotta.stato = "condizionamento"
    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}?msg=Lotti+salvati", status_code=303)
