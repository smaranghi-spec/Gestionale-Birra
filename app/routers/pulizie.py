from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date
from ..db import SessionLocal
from ..models import RegistroPulizie

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TIPI_PULIZIA = ["CIP", "Sanificazione", "Pulizia ordinaria", "Pulizia profonda",
                "Disinfezione", "Risciacquo", "Altro"]
LUOGHI = ["Pentola HLT", "Pentola mash", "Pentola bollitura", "Fermentatore A",
          "Fermentatore B", "Fermentatore C", "Sala cotta", "Magazzino",
          "Linea imbottigliamento", "Filtro", "Pumpe", "Altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/pulizie", response_class=HTMLResponse)
def lista(request: Request, db: Session = Depends(get_db)):
    items = db.query(RegistroPulizie).order_by(
        RegistroPulizie.data.desc(), RegistroPulizie.id.desc()
    ).all()
    return templates.TemplateResponse(request, "pulizie.html", {
        "pulizie": items,
        "tipi_pulizia": TIPI_PULIZIA,
        "luoghi": LUOGHI,
        "oggi": date.today().isoformat(),
        "session": request.session,
    })


@router.post("/pulizie")
def nuova(
    request: Request,
    data: str = Form(...),
    tipo_pulizia: str = Form(...),
    luogo: str = Form(...),
    detergente: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    operatore = request.session.get("nome", "")
    db.add(RegistroPulizie(
        data=data,
        tipo_pulizia=tipo_pulizia,
        luogo=luogo,
        operatore=operatore or None,
        detergente=detergente or None,
        note=note or None,
    ))
    db.commit()
    return RedirectResponse("/pulizie", status_code=303)


@router.post("/pulizie/{pid}/elimina")
def elimina(pid: int, db: Session = Depends(get_db)):
    p = db.query(RegistroPulizie).filter(RegistroPulizie.id == pid).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/pulizie", status_code=303)
