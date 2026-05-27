from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Cotta, LogCotta, Ricetta, STATI_COTTA

router = APIRouter()
templates = Jinja2Templates(directory="templates")

FASI_LABEL = {
    "pianificata": "Pianificata",
    "brewday": "Brew Day",
    "fermentazione": "Fermentazione",
    "secondaria": "Secondaria",
    "condizionamento": "Condizionamento",
    "imbottigliamento": "Imbottigliamento",
    "maturazione": "Maturazione",
    "pronta": "Pronta",
    "archiviata": "Archiviata",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _prossimo_stato(stato: str) -> Optional[str]:
    idx = STATI_COTTA.index(stato) if stato in STATI_COTTA else -1
    if idx >= 0 and idx < len(STATI_COTTA) - 1:
        return STATI_COTTA[idx + 1]
    return None


@router.get("/cotte", response_class=HTMLResponse)
def lista_cotte(request: Request, db: Session = Depends(get_db)):
    cotte = db.query(Cotta).order_by(Cotta.id.desc()).all()
    ricette = db.query(Ricetta).order_by(Ricetta.nome).all()

    contatori = {s: 0 for s in STATI_COTTA}
    for c in cotte:
        if c.stato in contatori:
            contatori[c.stato] += 1

    return templates.TemplateResponse(
        "cotte.html",
        {
            "request": request,
            "cotte": cotte,
            "ricette": ricette,
            "contatori": contatori,
            "fasi_label": FASI_LABEL,
            "stati": STATI_COTTA,
        },
    )


@router.post("/cotte/nuova")
def nuova_cotta(
    nome: str = Form(...),
    codice: str = Form(""),
    ricetta_id: int = Form(0),
    data_brew: str = Form(""),
    fermentatore: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    cotta = Cotta(
        nome=nome,
        codice=codice or None,
        ricetta_id=ricetta_id if ricetta_id else None,
        data_brew=data_brew or None,
        fermentatore=fermentatore or None,
        note=note or None,
        stato="pianificata",
    )
    db.add(cotta)
    db.flush()

    db.add(
        LogCotta(
            cotta_id=cotta.id,
            timestamp=_now_str(),
            fase="pianificata",
            tipo="evento",
            descrizione="Cotta creata",
        )
    )
    db.commit()
    return RedirectResponse(f"/cotte/{cotta.id}", status_code=303)


@router.get("/cotte/{cotta_id}", response_class=HTMLResponse)
def dettaglio_cotta(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    prossimo = _prossimo_stato(cotta.stato)
    idx_stato = STATI_COTTA.index(cotta.stato) if cotta.stato in STATI_COTTA else 0

    attenuation = None
    if cotta.ricetta:
        for ing in cotta.ricetta.ingredienti:
            if ing.categoria == "yeast" and ing.attenuation:
                attenuation = ing.attenuation
                break

    fg_stimata = None
    if cotta.og_reale and attenuation:
        fg_stimata = round(1 + (cotta.og_reale - 1) * (1 - attenuation / 100), 3)

    abv_calcolato = None
    if cotta.og_reale and cotta.fg_reale:
        abv_calcolato = round((cotta.og_reale - cotta.fg_reale) * 131.25, 1)
    elif cotta.og_reale and fg_stimata:
        abv_calcolato = round((cotta.og_reale - fg_stimata) * 131.25, 1)

    misure_sg = [
        {"t": e.timestamp, "v": e.valore}
        for e in cotta.log
        if e.tipo == "misura" and e.unita == "SG" and e.valore is not None
    ]
    misure_temp = [
        {"t": e.timestamp, "v": e.valore}
        for e in cotta.log
        if e.tipo == "misura" and e.unita == "°C" and e.valore is not None
    ]

    if cotta.og_reale and cotta.data_inoculo:
        og_entry = {"t": cotta.data_inoculo + " 00:00", "v": cotta.og_reale}
        if not misure_sg or misure_sg[0]["v"] != cotta.og_reale:
            misure_sg = [og_entry] + misure_sg

    if cotta.fg_reale and cotta.data_imbottigliamento:
        fg_entry = {"t": cotta.data_imbottigliamento + " 00:00", "v": cotta.fg_reale}
        if not misure_sg or misure_sg[-1]["v"] != cotta.fg_reale:
            misure_sg = misure_sg + [fg_entry]

    return templates.TemplateResponse(
        "dettaglio_cotta.html",
        {
            "request": request,
            "cotta": cotta,
            "log": list(reversed(cotta.log)),
            "prossimo_stato": prossimo,
            "prossimo_label": FASI_LABEL.get(prossimo, "") if prossimo else "",
            "idx_stato": idx_stato,
            "stati": STATI_COTTA,
            "fasi_label": FASI_LABEL,
            "fg_stimata": fg_stimata,
            "abv_calcolato": abv_calcolato,
            "oggi": date.today().strftime("%Y-%m-%d"),
            "misure_sg": misure_sg,
            "misure_temp": misure_temp,
        },
    )


@router.post("/cotte/{cotta_id}/avanza")
def avanza_stato(cotta_id: int, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    prossimo = _prossimo_stato(cotta.stato)
    if prossimo:
        vecchio = cotta.stato
        cotta.stato = prossimo

        if prossimo == "fermentazione" and not cotta.data_inoculo:
            cotta.data_inoculo = date.today().isoformat()
        if prossimo == "imbottigliamento" and not cotta.data_imbottigliamento:
            cotta.data_imbottigliamento = date.today().isoformat()

        db.add(
            LogCotta(
                cotta_id=cotta_id,
                timestamp=_now_str(),
                fase=prossimo,
                tipo="avanzamento",
                descrizione=f"Avanzato: {FASI_LABEL.get(vecchio)} → {FASI_LABEL.get(prossimo)}",
            )
        )
        db.commit()

    return RedirectResponse(f"/cotte/{cotta_id}", status_code=303)


@router.post("/cotte/{cotta_id}/aggiorna")
def aggiorna_cotta(
    cotta_id: int,
    volume_pre_bollitura: Optional[float] = Form(None),
    volume_post_bollitura: Optional[float] = Form(None),
    ph_mash: Optional[float] = Form(None),
    ph_pre_bollitura: Optional[float] = Form(None),
    temp_mash_gradi: Optional[float] = Form(None),
    durata_bollitura_min: Optional[int] = Form(None),
    efficienza_reale: Optional[float] = Form(None),
    og_reale: Optional[float] = Form(None),
    fg_reale: Optional[float] = Form(None),
    fermentatore: Optional[str] = Form(None),
    temp_fermentazione: Optional[float] = Form(None),
    data_inoculo: Optional[str] = Form(None),
    data_travasamento: Optional[str] = Form(None),
    temp_secondaria: Optional[float] = Form(None),
    data_imbottigliamento: Optional[str] = Form(None),
    tipo_packaging: Optional[str] = Form(None),
    volume_imbottigliato: Optional[float] = Form(None),
    carbonatazione_vols: Optional[float] = Form(None),
    priming_sugar_g: Optional[float] = Form(None),
    colore_visivo: Optional[str] = Form(None),
    limpidezza: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    fields = {
        "volume_pre_bollitura": volume_pre_bollitura,
        "volume_post_bollitura": volume_post_bollitura,
        "ph_mash": ph_mash,
        "ph_pre_bollitura": ph_pre_bollitura,
        "temp_mash_gradi": temp_mash_gradi,
        "durata_bollitura_min": durata_bollitura_min,
        "efficienza_reale": efficienza_reale,
        "og_reale": og_reale,
        "fg_reale": fg_reale,
        "fermentatore": fermentatore,
        "temp_fermentazione": temp_fermentazione,
        "data_inoculo": data_inoculo,
        "data_travasamento": data_travasamento,
        "temp_secondaria": temp_secondaria,
        "data_imbottigliamento": data_imbottigliamento,
        "tipo_packaging": tipo_packaging,
        "volume_imbottigliato": volume_imbottigliato,
        "carbonatazione_vols": carbonatazione_vols,
        "priming_sugar_g": priming_sugar_g,
        "colore_visivo": colore_visivo,
        "limpidezza": limpidezza,
        "note": note,
    }

    for k, v in fields.items():
        if v is not None and v != "":
            setattr(cotta, k, v)

    if og_reale and fg_reale:
        cotta.abv_reale = round((og_reale - fg_reale) * 131.25, 1)

    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}", status_code=303)


@router.post("/cotte/{cotta_id}/log")
def aggiungi_log(
    cotta_id: int,
    tipo: str = Form("nota"),
    descrizione: str = Form(...),
    valore: Optional[float] = Form(None),
    unita: Optional[str] = Form(None),
    fase: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    db.add(
        LogCotta(
            cotta_id=cotta_id,
            timestamp=_now_str(),
            fase=fase or cotta.stato,
            tipo=tipo,
            descrizione=descrizione,
            valore=valore,
            unita=unita or None,
            note=note or None,
        )
    )
    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}", status_code=303)


@router.post("/cotte/{cotta_id}/log/{log_id}/elimina")
def elimina_log(cotta_id: int, log_id: int, db: Session = Depends(get_db)):
    entry = (
        db.query(LogCotta)
        .filter(
            LogCotta.id == log_id,
            LogCotta.cotta_id == cotta_id,
        )
        .first()
    )
    if entry:
        db.delete(entry)
        db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}", status_code=303)


@router.post("/cotte/{cotta_id}/elimina")
def elimina_cotta(cotta_id: int, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if cotta:
        db.delete(cotta)
        db.commit()
    return RedirectResponse("/cotte", status_code=303)
