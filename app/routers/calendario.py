from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import EventoCalendario, Presenza, Ricetta

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TIPI_EVENTO = ["cotta", "imbottigliamento", "pulizia", "degustazione",
               "manutenzione", "consegna", "riunione", "altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/calendario", response_class=HTMLResponse)
def calendario(request: Request, mese: str = None, db: Session = Depends(get_db)):
    oggi = date.today()
    if mese:
        anno, m = map(int, mese.split("-"))
        mese_corrente = date(anno, m, 1)
    else:
        mese_corrente = date(oggi.year, oggi.month, 1)

    mese_prec = (mese_corrente - timedelta(days=1)).replace(day=1)
    mese_succ = (mese_corrente + timedelta(days=32)).replace(day=1)

    primo_giorno = mese_corrente.weekday()  # 0=lun
    if mese_corrente.month == 12:
        ultimo = date(mese_corrente.year + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo = date(mese_corrente.year, mese_corrente.month + 1, 1) - timedelta(days=1)

    giorni = list(range(1, ultimo.day + 1))

    mese_str = mese_corrente.strftime("%Y-%m")
    eventi = db.query(EventoCalendario).filter(
        EventoCalendario.data.startswith(mese_str)
    ).order_by(EventoCalendario.data, EventoCalendario.ora).all()
    eventi_per_giorno: dict = {}
    for e in eventi:
        d = int(e.data[8:10])
        eventi_per_giorno.setdefault(d, []).append(e)

    presenze = db.query(Presenza).filter(
        Presenza.data.startswith(mese_str)
    ).order_by(Presenza.data).all()

    utente_nome = request.session.get("nome", "")
    presenza_oggi = db.query(Presenza).filter(
        Presenza.data == oggi.isoformat(),
        Presenza.utente_nome == utente_nome,
    ).first()

    ricette = db.query(Ricetta).order_by(Ricetta.nome).all()

    return templates.TemplateResponse(request, "calendario.html", {
        "mese_corrente": mese_corrente,
        "mese_prec": mese_prec.strftime("%Y-%m"),
        "mese_succ": mese_succ.strftime("%Y-%m"),
        "mese_nome": mese_corrente.strftime("%B %Y").capitalize(),
        "primo_giorno": primo_giorno,
        "giorni": giorni,
        "eventi_per_giorno": eventi_per_giorno,
        "presenze": presenze,
        "presenza_oggi": presenza_oggi,
        "oggi": oggi.isoformat(),
        "tipi_evento": TIPI_EVENTO,
        "ricette": ricette,
        "session": request.session,
    })


@router.post("/calendario/evento")
def nuovo_evento(
    data: str = Form(...),
    ora: str = Form(""),
    tipo: str = Form("altro"),
    titolo: str = Form(...),
    descrizione: str = Form(""),
    ricetta_id: int = Form(0),
    responsabile: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(EventoCalendario(
        data=data, ora=ora or None, tipo=tipo, titolo=titolo,
        descrizione=descrizione or None,
        ricetta_id=ricetta_id if ricetta_id else None,
        responsabile=responsabile or None,
    ))
    db.commit()
    mese = data[:7]
    return RedirectResponse(f"/calendario?mese={mese}", status_code=303)


@router.post("/calendario/evento/{eid}/completa")
def completa_evento(eid: int, db: Session = Depends(get_db)):
    e = db.query(EventoCalendario).filter(EventoCalendario.id == eid).first()
    if e:
        e.completato = not e.completato
        db.commit()
        mese = e.data[:7]
        return RedirectResponse(f"/calendario?mese={mese}", status_code=303)
    return RedirectResponse("/calendario", status_code=303)


@router.post("/calendario/evento/{eid}/elimina")
def elimina_evento(eid: int, db: Session = Depends(get_db)):
    e = db.query(EventoCalendario).filter(EventoCalendario.id == eid).first()
    mese = e.data[:7] if e else None
    if e:
        db.delete(e)
        db.commit()
    return RedirectResponse(f"/calendario?mese={mese}" if mese else "/calendario", status_code=303)


@router.post("/presenze/checkin")
def checkin(request: Request, db: Session = Depends(get_db)):
    oggi = date.today().isoformat()
    nome = request.session.get("nome", "Anonimo")
    uid = request.session.get("user_id")
    p = db.query(Presenza).filter(Presenza.data == oggi, Presenza.utente_nome == nome).first()
    if not p:
        now = datetime.now().strftime("%H:%M")
        db.add(Presenza(data=oggi, utente_id=uid, utente_nome=nome, check_in=now))
        db.commit()
    return RedirectResponse("/calendario", status_code=303)


@router.post("/presenze/checkout")
def checkout(request: Request, db: Session = Depends(get_db)):
    oggi = date.today().isoformat()
    nome = request.session.get("nome", "Anonimo")
    p = db.query(Presenza).filter(Presenza.data == oggi, Presenza.utente_nome == nome).first()
    if p and not p.check_out:
        now = datetime.now().strftime("%H:%M")
        p.check_out = now
        if p.check_in:
            from datetime import datetime as dt
            tin = dt.strptime(p.check_in, "%H:%M")
            tout = dt.strptime(now, "%H:%M")
            diff = (tout - tin).total_seconds() / 3600
            p.ore_totali = round(diff, 2)
        db.commit()
    return RedirectResponse("/calendario", status_code=303)


@router.post("/presenze/manuale")
def presenza_manuale(
    request: Request,
    data: str = Form(...),
    utente_nome: str = Form(...),
    check_in: str = Form(""),
    check_out: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    uid = request.session.get("user_id") if utente_nome == request.session.get("nome") else None
    ore = None
    if check_in and check_out:
        from datetime import datetime as dt
        try:
            tin = dt.strptime(check_in, "%H:%M")
            tout = dt.strptime(check_out, "%H:%M")
            ore = round((tout - tin).total_seconds() / 3600, 2)
        except Exception:
            pass
    existing = db.query(Presenza).filter(
        Presenza.data == data, Presenza.utente_nome == utente_nome
    ).first()
    if existing:
        existing.check_in = check_in or existing.check_in
        existing.check_out = check_out or existing.check_out
        if ore is not None:
            existing.ore_totali = ore
        existing.note = note or existing.note
    else:
        db.add(Presenza(
            data=data, utente_id=uid, utente_nome=utente_nome,
            check_in=check_in or None, check_out=check_out or None,
            ore_totali=ore, note=note or None,
        ))
    db.commit()
    return RedirectResponse("/calendario", status_code=303)
