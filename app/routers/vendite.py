from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date

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
def lista_vendite(request: Request, db: Session = Depends(get_db)):
    vendite = db.query(Vendita).order_by(Vendita.data.desc(), Vendita.id.desc()).all()
    ricette = db.query(Ricetta).order_by(Ricetta.nome).all()

    totale_fatturato = sum(v.prezzo_euro or 0 for v in vendite)
    totale_litri = sum(v.quantita_litri or 0 for v in vendite)
    n_clienti = len(set(v.cliente for v in vendite if v.cliente))

    from collections import defaultdict
    per_mese: dict = defaultdict(float)
    for v in vendite:
        if v.data and len(v.data) >= 7:
            mese = v.data[:7]
            per_mese[mese] += v.prezzo_euro or 0
    trend = sorted(per_mese.items())[-6:]

    return templates.TemplateResponse(request, "vendite.html", {
        "vendite": vendite,
        "ricette": ricette,
        "totale_fatturato": round(totale_fatturato, 2),
        "totale_litri": round(totale_litri, 1),
        "n_clienti": n_clienti,
        "trend": trend,
        "oggi": date.today().isoformat(),
        "session": request.session,
    })


@router.post("/vendite")
def crea_vendita(
    request: Request,
    data: str = Form(...),
    cliente: str = Form(""),
    prodotto: str = Form(...),
    ricetta_id: int = Form(0),
    quantita_litri: float = Form(None),
    n_bottiglie: int = Form(None),
    prezzo_euro: float = Form(None),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    v = Vendita(
        data=data,
        cliente=cliente.strip() or None,
        prodotto=prodotto.strip(),
        ricetta_id=ricetta_id if ricetta_id else None,
        quantita_litri=quantita_litri,
        n_bottiglie=n_bottiglie,
        prezzo_euro=prezzo_euro,
        note=note.strip() or None,
    )
    db.add(v)
    db.commit()
    return RedirectResponse("/vendite", status_code=303)


@router.get("/vendite/{vendita_id}/elimina")
def elimina_vendita(vendita_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendita).filter(Vendita.id == vendita_id).first()
    if v:
        db.delete(v)
        db.commit()
    return RedirectResponse("/vendite", status_code=303)
