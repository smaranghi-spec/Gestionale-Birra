from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
from ..db import SessionLocal
from ..models import Vendita, Ricetta

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
    quantita_litri: float = Form(None),
    n_bottiglie: int = Form(None),
    prezzo_euro: float = Form(None),
    note: str = Form(""),
    stato: str = Form("confermata"),
    db: Session = Depends(get_db),
):
    db.add(Vendita(
        data=data,
        cliente=cliente.strip() or None,
        prodotto=prodotto.strip(),
        ricetta_id=ricetta_id if ricetta_id else None,
        quantita_litri=quantita_litri,
        n_bottiglie=n_bottiglie,
        prezzo_euro=prezzo_euro,
        note=note.strip() or None,
        stato=stato if stato in ("bozza", "confermata") else "confermata",
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
