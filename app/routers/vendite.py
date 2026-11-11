from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
from ..db import SessionLocal
from ..models import Vendita, Ricetta, ProdottoFinito

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/vendite", response_class=HTMLResponse)
def lista_vendite(request: Request, stato: str = None, db: Session = Depends(get_db)):
    query = db.query(Vendita)
    if stato:
        query = query.filter(Vendita.stato == stato)
    vendite = query.order_by(Vendita.data.desc(), Vendita.id.desc()).all()
    ricette = db.query(Ricetta).order_by(Ricetta.nome).all()
    lotti_finiti = (
        db.query(ProdottoFinito)
        .filter(ProdottoFinito.n_pezzi_disponibili > 0)
        .order_by(ProdottoFinito.data_imbottigliamento.asc(), ProdottoFinito.id.asc())
        .all()
    )

    confermate = [v for v in vendite if (v.stato or "confermata") == "confermata"]
    n_bozze = db.query(Vendita).filter(Vendita.stato == "bozza").count()

    fatturato = sum(v.prezzo_euro or 0 for v in confermate)
    litri = sum(v.quantita_litri or 0 for v in confermate)
    n_clienti = len(set(v.cliente for v in confermate if v.cliente))

    from collections import defaultdict
    per_mese: dict = defaultdict(float)
    for v in confermate:
        if v.data and len(v.data) >= 7:
            per_mese[v.data[:7]] += v.prezzo_euro or 0
    trend = sorted(per_mese.items())[-6:]

    return templates.TemplateResponse(request, "vendite.html", {
        "vendite": vendite,
        "ricette": ricette,
        "lotti_finiti": lotti_finiti,
        "fatturato": round(fatturato, 2),
        "litri": round(litri, 1),
        "n_clienti": n_clienti,
        "trend": trend,
        "oggi": date.today().isoformat(),
        "n_bozze": n_bozze,
        "stato_filtro": stato,
        "session": request.session,
    })


@router.post("/vendite")
def crea_vendita(
    data: str = Form(...),
    cliente: str = Form(""),
    prodotto: str = Form(...),
    ricetta_id: int = Form(0),
    prodotto_finito_id: int = Form(0),
    quantita_litri: float = Form(None),
    n_bottiglie: int = Form(None),
    prezzo_euro: float = Form(None),
    note: str = Form(""),
    stato: str = Form("confermata"),
    db: Session = Depends(get_db),
):
    pf = db.query(ProdottoFinito).filter(ProdottoFinito.id == prodotto_finito_id).first() if prodotto_finito_id else None
    stato_eff = stato if stato in ("bozza", "confermata") else "confermata"
    note_eff = note.strip()

    if pf:
        if not ricetta_id and pf.cotta and pf.cotta.ricetta_id:
            ricetta_id = pf.cotta.ricetta_id
        pezzi = n_bottiglie or 1
        if not quantita_litri and pf.formato_ml:
            quantita_litri = round((pezzi * pf.formato_ml) / 1000.0, 2)
        if prezzo_euro is None and pf.prezzo_vendita:
            prezzo_euro = round(pezzi * pf.prezzo_vendita, 2)
        lotto_tag = f"[Lotto {pf.codice_lotto or pf.codice}]"
        if lotto_tag not in note_eff:
            note_eff = f"{lotto_tag} {note_eff}".strip()
        if stato_eff == "confermata":
            pf.n_pezzi_disponibili = max(0, (pf.n_pezzi_disponibili or 0) - pezzi)
            if pf.n_pezzi_disponibili == 0:
                pf.stato = "esaurito"

    db.add(Vendita(
        data=data,
        cliente=cliente.strip() or None,
        prodotto=prodotto.strip(),
        ricetta_id=ricetta_id if ricetta_id else None,
        quantita_litri=quantita_litri,
        n_bottiglie=n_bottiglie,
        prezzo_euro=prezzo_euro,
        note=note_eff or None,
        stato=stato_eff,
    ))
    db.commit()
    return RedirectResponse("/vendite", status_code=303)


@router.post("/vendite/{vid}/conferma")
def conferma_vendita(vid: int, db: Session = Depends(get_db)):
    v = db.query(Vendita).filter(Vendita.id == vid).first()
    if v:
        v.stato = "confermata"
        db.commit()
    return RedirectResponse("/vendite", status_code=303)


@router.post("/vendite/{vid}/elimina")
def elimina_vendita(vid: int, db: Session = Depends(get_db)):
    v = db.query(Vendita).filter(Vendita.id == vid).first()
    if v:
        db.delete(v)
        db.commit()
    return RedirectResponse("/vendite", status_code=303)
