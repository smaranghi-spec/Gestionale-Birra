from datetime import datetime
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import ProfiloSocio, User

router = APIRouter()
templates = Jinja2Templates(directory="templates")

STATI = ["attivo", "sospeso", "uscito"]
RUOLI_INTERNI = ["", "Mastro Birraio", "Birraio", "Tesoriere", "Segretario", "Presidente", "Vice-Presidente", "Socio Fondatore"]
ANNO_CORRENTE = datetime.now().year


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_admin(request: Request):
    return request.session.get("ruolo") == "admin"


@router.get("/soci", response_class=HTMLResponse)
def lista_soci(request: Request, stato: str = None, msg: str = None, db: Session = Depends(get_db)):
    query = db.query(ProfiloSocio)
    if stato:
        query = query.filter(ProfiloSocio.stato_socio == stato)
    soci = query.order_by(ProfiloSocio.cognome, ProfiloSocio.nome).all()

    totale = db.query(ProfiloSocio).count()
    per_stato = {}
    for s in db.query(ProfiloSocio).all():
        per_stato[s.stato_socio] = per_stato.get(s.stato_socio, 0) + 1

    quota_ok = sum(1 for s in soci if s.quota_versata and s.stato_socio == "attivo")
    quota_mancante = sum(1 for s in soci if not s.quota_versata and s.stato_socio == "attivo")

    utenti_liberi = db.query(User).filter(
        ~User.id.in_(
            [s.user_id for s in db.query(ProfiloSocio).filter(ProfiloSocio.user_id.isnot(None)).all()]
        )
    ).order_by(User.nome).all()

    return templates.TemplateResponse(request, "soci.html", {
        "soci": soci,
        "stato_filtro": stato,
        "msg": msg,
        "totale": totale,
        "per_stato": per_stato,
        "quota_ok": quota_ok,
        "quota_mancante": quota_mancante,
        "stati": STATI,
        "ruoli_interni": RUOLI_INTERNI,
        "anno_corrente": ANNO_CORRENTE,
        "utenti_liberi": utenti_liberi,
        "session": request.session,
    })


@router.post("/soci/nuovo")
def nuovo_socio(
    nome: str = Form(...),
    cognome: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    data_nascita: str = Form(""),
    codice_fiscale: str = Form(""),
    anno_iscrizione: str = Form(""),
    quota_annuale: str = Form(""),
    ruolo_interno: str = Form(""),
    note: str = Form(""),
    user_id: str = Form(""),
    db: Session = Depends(get_db),
):
    s = ProfiloSocio(
        nome=nome.strip(),
        cognome=cognome.strip() or None,
        email=email.strip() or None,
        telefono=telefono.strip() or None,
        data_nascita=data_nascita or None,
        codice_fiscale=codice_fiscale.strip() or None,
        anno_iscrizione=int(anno_iscrizione) if anno_iscrizione.strip().isdigit() else ANNO_CORRENTE,
        quota_annuale=float(quota_annuale) if quota_annuale.strip() else None,
        ruolo_interno=ruolo_interno or None,
        note=note.strip() or None,
        user_id=int(user_id) if user_id.strip().isdigit() else None,
        stato_socio="attivo",
    )
    db.add(s)
    db.commit()
    return RedirectResponse("/soci?msg=Socio+aggiunto", status_code=303)


@router.get("/soci/{sid}", response_class=HTMLResponse)
def dettaglio_socio(sid: int, request: Request, msg: str = None, db: Session = Depends(get_db)):
    s = db.query(ProfiloSocio).filter(ProfiloSocio.id == sid).first()
    if not s:
        return RedirectResponse("/soci", status_code=303)
    utenti_liberi = db.query(User).filter(
        (User.id == s.user_id) |
        ~User.id.in_(
            [x.user_id for x in db.query(ProfiloSocio).filter(ProfiloSocio.user_id.isnot(None)).all()]
        )
    ).order_by(User.nome).all()
    return templates.TemplateResponse(request, "dettaglio_socio.html", {
        "s": s,
        "msg": msg,
        "stati": STATI,
        "ruoli_interni": RUOLI_INTERNI,
        "anno_corrente": ANNO_CORRENTE,
        "utenti_liberi": utenti_liberi,
        "is_admin": _require_admin(request),
        "session": request.session,
    })


@router.post("/soci/{sid}/aggiorna")
def aggiorna_socio(
    sid: int,
    nome: str = Form(...),
    cognome: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    data_nascita: str = Form(""),
    codice_fiscale: str = Form(""),
    anno_iscrizione: str = Form(""),
    quota_annuale: str = Form(""),
    quota_versata: str = Form(""),
    stato_socio: str = Form("attivo"),
    ruolo_interno: str = Form(""),
    note: str = Form(""),
    user_id: str = Form(""),
    db: Session = Depends(get_db),
):
    s = db.query(ProfiloSocio).filter(ProfiloSocio.id == sid).first()
    if not s:
        return RedirectResponse("/soci", status_code=303)
    s.nome = nome.strip()
    s.cognome = cognome.strip() or None
    s.email = email.strip() or None
    s.telefono = telefono.strip() or None
    s.data_nascita = data_nascita or None
    s.codice_fiscale = codice_fiscale.strip() or None
    s.anno_iscrizione = int(anno_iscrizione) if anno_iscrizione.strip().isdigit() else s.anno_iscrizione
    s.quota_annuale = float(quota_annuale) if quota_annuale.strip() else None
    s.quota_versata = quota_versata == "1"
    s.stato_socio = stato_socio
    s.ruolo_interno = ruolo_interno or None
    s.note = note.strip() or None
    s.user_id = int(user_id) if user_id.strip().isdigit() else None
    db.commit()
    return RedirectResponse(f"/soci/{sid}?msg=Salvato", status_code=303)


@router.post("/soci/{sid}/quota")
def toggle_quota(sid: int, db: Session = Depends(get_db)):
    s = db.query(ProfiloSocio).filter(ProfiloSocio.id == sid).first()
    if s:
        s.quota_versata = not s.quota_versata
        db.commit()
    return RedirectResponse("/soci", status_code=303)


@router.post("/soci/{sid}/elimina")
def elimina_socio(sid: int, request: Request, db: Session = Depends(get_db)):
    if not _require_admin(request):
        return RedirectResponse("/soci", status_code=303)
    s = db.query(ProfiloSocio).filter(ProfiloSocio.id == sid).first()
    if s:
        db.delete(s)
        db.commit()
    return RedirectResponse("/soci?msg=Socio+eliminato", status_code=303)
