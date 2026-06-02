"""Lista acquisti da fare (shopping list)."""
from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import ListaAcquisti, OrdineAcquisto, RigaOrdine

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIE = ["ingrediente", "consumabile", "attrezzatura", "accessorio", "packaging", "chimico", "altro"]
UNITA = ["kg", "g", "L", "mL", "pz", "rotolo", "busta", "flacone", "altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/lista-acquisti", response_class=HTMLResponse)
def lista(request: Request, db: Session = Depends(get_db)):
    items = db.query(ListaAcquisti).order_by(
        ListaAcquisti.completato, ListaAcquisti.priorita, ListaAcquisti.id.desc()
    ).all()
    da_fare = [i for i in items if not i.completato]
    completati = [i for i in items if i.completato]
    return templates.TemplateResponse(request, "lista_acquisti.html", {
        "da_fare": da_fare,
        "completati": completati,
        "categorie": CATEGORIE,
        "unita": UNITA,
        "session": request.session,
    })


@router.post("/lista-acquisti/aggiungi")
def aggiungi(
    nome: str = Form(...),
    categoria: str = Form("ingrediente"),
    quantita: float = Form(1.0),
    unita: str = Form("kg"),
    fornitore: str = Form(""),
    priorita: int = Form(2),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(ListaAcquisti(
        nome=nome, categoria=categoria, quantita=quantita, unita=unita,
        fornitore=fornitore or None, priorita=priorita, note=note or None,
    ))
    db.commit()
    return RedirectResponse("/lista-acquisti", status_code=303)


@router.post("/lista-acquisti/{iid}/completa")
def completa(iid: int, db: Session = Depends(get_db)):
    item = db.query(ListaAcquisti).filter(ListaAcquisti.id == iid).first()
    if item:
        item.completato = not item.completato
        db.commit()
    return RedirectResponse("/lista-acquisti", status_code=303)


@router.post("/lista-acquisti/{iid}/elimina")
def elimina(iid: int, db: Session = Depends(get_db)):
    item = db.query(ListaAcquisti).filter(ListaAcquisti.id == iid).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/lista-acquisti", status_code=303)


@router.post("/lista-acquisti/svuota-completati")
def svuota_completati(db: Session = Depends(get_db)):
    db.query(ListaAcquisti).filter(ListaAcquisti.completato == True).delete()
    db.commit()
    return RedirectResponse("/lista-acquisti", status_code=303)


@router.post("/lista-acquisti/crea-ordine")
def crea_ordine_da_lista(db: Session = Depends(get_db)):
    """Converte tutti gli item non completati in un ordine di acquisto."""
    items = db.query(ListaAcquisti).filter(ListaAcquisti.completato == False).all()
    if not items:
        return RedirectResponse("/lista-acquisti?msg=Nessun+articolo+da+ordinare", status_code=303)

    ordine = OrdineAcquisto(
        data=datetime.now().strftime("%Y-%m-%d"),
        stato="bozza",
        note="Creato da lista acquisti",
    )
    db.add(ordine)
    db.flush()
    for i in items:
        db.add(RigaOrdine(
            ordine_id=ordine.id, nome=i.nome, categoria=i.categoria,
            quantita=i.quantita, unita=i.unita, note=i.note,
        ))
    db.commit()
    return RedirectResponse(f"/acquisti/{ordine.id}", status_code=303)
