import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Cotta, LogCotta, Ricetta, STATI_COTTA, Degustazione, InventarioItem

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
    except Exception:
        db.rollback()
        raise
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

    # Dati grafico — misurazioni SG e temperatura in ordine cronologico

    misure_sg = [
        {"t": e.timestamp, "v": e.valore}
        for e in cotta.log
        if (e.unita == "SG" or e.tipo in ("densita", "misura")) and e.valore is not None and e.unita != "°C"
    ]
    misure_temp = [
        {"t": e.timestamp, "v": e.valore}
        for e in cotta.log
        if (e.unita == "°C" or e.tipo in ("temperatura", "temp")) and e.valore is not None and e.unita != "SG"
    ]

    # Aggiungi OG al grafico come primo punto se disponibile e non già registrato
    if cotta.og_reale and cotta.data_inoculo:
        og_entry = {"t": cotta.data_inoculo + " 00:00", "v": cotta.og_reale}
        if not misure_sg or misure_sg[0]["v"] != cotta.og_reale:
            misure_sg = [og_entry] + misure_sg
    if cotta.fg_reale and cotta.data_imbottigliamento:
        fg_entry = {"t": cotta.data_imbottigliamento + " 00:00", "v": cotta.fg_reale}
        if not misure_sg or misure_sg[-1]["v"] != cotta.fg_reale:
            misure_sg = misure_sg + [fg_entry]

    degustazioni = (
        db.query(Degustazione)
        .filter(Degustazione.cotta_id == cotta_id)
        .order_by(Degustazione.data.desc())
        .all()
    )

    return templates.TemplateResponse(
        request,
        "dettaglio_cotta.html",
        {
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
            "degustazioni": degustazioni,
            "session": request.session,
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


@router.post("/cotte/{cotta_id}/log-bulk")
async def aggiungi_log_bulk(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    """Inserimento massivo di letture fermentazione: più righe (data/temp/densità) in un colpo."""
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    form = await request.form()
    n_righe = 0
    i = 0
    while f"data_{i}" in form:
        data_i = form.get(f"data_{i}")
        temp_i = form.get(f"temp_{i}")
        dens_i = form.get(f"densita_{i}")
        note_i = form.get(f"note_{i}")
        if data_i and (temp_i or dens_i):
            timestamp = data_i.strip()
            if temp_i:
                try:
                    db.add(LogCotta(
                        cotta_id=cotta_id, timestamp=timestamp, fase=cotta.stato,
                        tipo="temperatura", descrizione="Lettura temperatura (bulk)",
                        valore=float(temp_i), unita="°C", note=note_i or None,
                    ))
                    n_righe += 1
                except ValueError:
                    pass
            if dens_i:
                try:
                    db.add(LogCotta(
                        cotta_id=cotta_id, timestamp=timestamp, fase=cotta.stato,
                        tipo="densita", descrizione="Lettura densità (bulk)",
                        valore=float(dens_i), unita="SG", note=note_i or None,
                    ))
                    n_righe += 1
                except ValueError:
                    pass
        i += 1

    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}?msg={n_righe}+letture+aggiunte", status_code=303)


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


@router.get("/cotte/{cotta_id}/vai-produzione", response_class=HTMLResponse)
def vai_produzione_page(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)
    if not cotta.ricetta:
        return RedirectResponse(f"/cotte/{cotta_id}?msg=Nessuna+ricetta+collegata", status_code=303)

    ricetta = cotta.ricetta
    vol_ricetta = ricetta.volume_target_litri or 20.0

    # Scala ingredienti in base al volume batch (di default = volume ricetta)
    vol_batch = cotta.volume_post_bollitura or vol_ricetta
    fattore = vol_batch / vol_ricetta if vol_ricetta else 1.0

    ingredienti_scalati = []
    for ing in ricetta.ingredienti:
        qty_scalata = round(ing.quantita * fattore, 3)
        # Controlla disponibilità in inventario
        inv = db.query(InventarioItem).filter(
            InventarioItem.nome.ilike(f"%{ing.nome[:20]}%")
        ).first()
        disponibile = inv.quantita if inv else None
        ingredienti_scalati.append({
            "id": ing.id,
            "nome": ing.nome,
            "categoria": ing.categoria,
            "quantita_ricetta": ing.quantita,
            "unita": ing.unita,
            "quantita_scalata": qty_scalata,
            "disponibile": disponibile,
            "inv_id": inv.id if inv else None,
            "sufficiente": (disponibile is None or disponibile >= qty_scalata),
        })

    return templates.TemplateResponse(request, "vai_produzione.html", {
        "cotta": cotta,
        "ricetta": ricetta,
        "vol_ricetta": vol_ricetta,
        "vol_batch": vol_batch,
        "fattore": round(fattore, 3),
        "ingredienti": ingredienti_scalati,
        "session": request.session,
    })


@router.post("/cotte/{cotta_id}/vai-produzione")
async def vai_produzione_submit(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    vol_batch = float(form.get("vol_batch", 0) or 0)
    scarica_inventario = form.get("scarica_inventario") == "1"

    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta or not cotta.ricetta:
        return RedirectResponse("/cotte", status_code=303)

    ricetta = cotta.ricetta
    vol_ricetta = ricetta.volume_target_litri or 20.0
    if vol_batch <= 0:
        vol_batch = vol_ricetta
    fattore = vol_batch / vol_ricetta if vol_ricetta else 1.0

    # Aggiorna volume cotta
    cotta.volume_post_bollitura = vol_batch

    # Avanza a brewday se era pianificata
    if cotta.stato == "pianificata":
        cotta.stato = "brewday"
        db.add(LogCotta(
            cotta_id=cotta_id,
            timestamp=_now_str(),
            fase="brewday",
            tipo="evento",
            descrizione=f"Avviata produzione — volume: {vol_batch}L (fattore scala: ×{round(fattore,3)})",
        ))

    # Scala ingredienti e scarica inventario se richiesto
    movimenti = []
    for ing in ricetta.ingredienti:
        qty_scalata = round(ing.quantita * fattore, 3)
        log_desc = f"Ingrediente: {ing.nome} × {qty_scalata} {ing.unita}"
        if scarica_inventario:
            inv = db.query(InventarioItem).filter(
                InventarioItem.nome.ilike(f"%{ing.nome[:20]}%")
            ).first()
            if inv and inv.quantita >= qty_scalata:
                inv.quantita = round(inv.quantita - qty_scalata, 4)
                inv.ultimo_aggiornamento = _now_str()
                log_desc += f" (scaricato da magazzino)"
        movimenti.append(log_desc)

    if movimenti:
        db.add(LogCotta(
            cotta_id=cotta_id,
            timestamp=_now_str(),
            fase="brewday",
            tipo="nota",
            descrizione="Ingredienti scalati: " + " | ".join(movimenti[:5]) + (f" + altri {len(movimenti)-5}" if len(movimenti)>5 else ""),
        ))

    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}?msg=Produzione+avviata", status_code=303)


@router.post("/cotte/{cotta_id}/elimina")
def elimina_cotta(cotta_id: int, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if cotta:
        try:
            from ..models import LetturaDensita, LogCotta, Degustazione, AggiuntaCotta
            db.query(LetturaDensita).filter(LetturaDensita.cotta_id == cotta_id).delete(synchronize_session=False)
            db.query(LogCotta).filter(LogCotta.cotta_id == cotta_id).delete(synchronize_session=False)
            db.query(Degustazione).filter(Degustazione.cotta_id == cotta_id).delete(synchronize_session=False)
            db.query(AggiuntaCotta).filter(AggiuntaCotta.cotta_id == cotta_id).delete(synchronize_session=False)
            db.delete(cotta)
            db.commit()
        except Exception:
            db.rollback()
            return RedirectResponse("/cotte?msg=Errore+durante+l+eliminazione+della+cotta", status_code=303)
    return RedirectResponse("/cotte", status_code=303)


@router.get("/degustazioni", response_class=HTMLResponse)
def lista_degustazioni(request: Request, db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    cottas = (
        db.query(Cotta)
        .options(joinedload(Cotta.degustazioni), joinedload(Cotta.ricetta))
        .join(Degustazione, Degustazione.cotta_id == Cotta.id)
        .distinct()
        .order_by(Cotta.data_brew.desc(), Cotta.id.desc())
        .all()
    )
    # Ordina le degustazioni di ciascuna cotta per data desc
    for c in cottas:
        c.degustazioni.sort(key=lambda d: d.data, reverse=True)
    return templates.TemplateResponse("degustazioni.html", {
        "request": request,
        "cottas": cottas,
        "session": request.session,
    })


@router.post("/cotte/{cotta_id}/degustazioni")
def aggiungi_degustazione(
    cotta_id: int,
    data: str = Form(""),
    degustatore: str = Form(""),
    # Esame Visivo
    limpidezza: float = Form(0),
    colore: float = Form(0),
    schiuma: float = Form(0),
    # Esame Olfattivo
    intensita_olfattiva: float = Form(0),
    finezza_olfattiva: float = Form(0),
    complessita_olfattiva: float = Form(0),
    # Esame Gusto-Olfattivo
    corpo: float = Form(0),
    equilibrio: float = Form(0),
    persistenza_gusto_olfattiva: float = Form(0),
    # Impressione Generale
    impressione_generale: float = Form(0),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    from datetime import date as _date
    ub_fields = [limpidezza, colore, schiuma, intensita_olfattiva, finezza_olfattiva,
                 complessita_olfattiva, corpo, equilibrio, persistenza_gusto_olfattiva,
                 impressione_generale]
    totale_ub = round(sum(ub_fields), 1)
    d = Degustazione(
        cotta_id=cotta_id,
        data=data or _date.today().isoformat(),
        degustatore=degustatore or None,
        limpidezza=limpidezza or None,
        colore=colore or None,
        schiuma=schiuma or None,
        intensita_olfattiva=intensita_olfattiva or None,
        finezza_olfattiva=finezza_olfattiva or None,
        complessita_olfattiva=complessita_olfattiva or None,
        corpo=corpo or None,
        equilibrio=equilibrio or None,
        persistenza_gusto_olfattiva=persistenza_gusto_olfattiva or None,
        impressione_generale=impressione_generale or None,
        note=note or None,
        voto=totale_ub if totale_ub > 0 else None,
    )
    db.add(d)
    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}#degustazioni", status_code=303)


@router.post("/cotte/{cotta_id}/degustazioni/{deg_id}/elimina")
def elimina_degustazione(cotta_id: int, deg_id: int, db: Session = Depends(get_db)):
    d = db.query(Degustazione).filter(
        Degustazione.id == deg_id,
        Degustazione.cotta_id == cotta_id,
    ).first()
    if d:
        db.delete(d)
        db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}#degustazioni", status_code=303)


@router.get("/cotte/{cotta_id}/stampa", response_class=HTMLResponse)
def stampa_scheda_cotta(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    ricetta = cotta.ricetta
    ingredienti = ricetta.ingredienti if ricetta else []

    grani = []
    luppoli = []
    lieviti = []
    misc = []

    tot_grani_kg = 0.0
    for ing in ingredienti:
        cat = (ing.categoria or "").lower()
        q = ing.quantita or 0.0
        u = (ing.unita or "").lower()

        if cat in ("grain", "fermentabile", "malto"):
            q_kg = q * 0.001 if u in ("g", "gr") else q
            tot_grani_kg += q_kg
            grani.append({
                "nome": ing.nome,
                "quantita": q_kg,
                "unita": "kg",
                "colore": ing.color_srm,
                "note": ing.note or ""
            })
        elif cat in ("hop", "luppolo"):
            q_g = q * 1000 if u == "kg" else q
            luppoli.append({
                "nome": ing.nome,
                "quantita": q_g,
                "unita": "g",
                "time_min": ing.time_min if ing.time_min is not None else 0,
                "alpha_acid": ing.alpha_acid,
                "hop_use": ing.hop_use or "Boil",
                "hop_form": ing.hop_form or "Pellet",
                "note": ing.note or ""
            })
        elif cat in ("yeast", "lievito"):
            lieviti.append({
                "nome": ing.nome,
                "quantita": q,
                "unita": ing.unita or "bustina",
                "attenuation": ing.attenuation,
                "yeast_form": ing.yeast_form or "Secco",
                "note": ing.note or ""
            })
        else:
            misc.append({
                "nome": ing.nome,
                "quantita": q,
                "unita": ing.unita or "",
                "time_min": ing.time_min,
                "note": ing.note or ""
            })

    for g in grani:
        g["perc"] = round((g["quantita"] / tot_grani_kg * 100), 1) if tot_grani_kg > 0 else 0.0

    luppoli.sort(key=lambda x: (x["time_min"] if x["time_min"] is not None else -1), reverse=True)

    mash_steps = []
    if ricetta and ricetta.profilo_mash and ricetta.profilo_mash.steps_json:
        try:
            raw_steps = json.loads(ricetta.profilo_mash.steps_json)
            if isinstance(raw_steps, list):
                for s in raw_steps:
                    if isinstance(s, dict):
                        mash_steps.append({
                            "nome": s.get("nome") or s.get("step_name") or "Step",
                            "temp": s.get("temp_gradi") or s.get("temp") or s.get("step_temp") or "-",
                            "tempo": s.get("durata_min") or s.get("durata") or s.get("step_time") or s.get("tempo") or "-"
                        })
        except Exception:
            mash_steps = []

    if not mash_steps:
        mash_steps = [
            {"nome": "Ammostamento (Saccarificazione)", "temp": 66, "tempo": 60},
            {"nome": "Mash-Out", "temp": 77, "tempo": 10}
        ]

    vol_target = ricetta.volume_target_litri if (ricetta and ricetta.volume_target_litri) else 20.0
    stats = {}
    if ricetta:
        from ..stats import calcola_stats
        stats = calcola_stats(ricetta, ingredienti)

    tot_grani_kg = round(tot_grani_kg, 2)
    litri_mash = round(tot_grani_kg * 3.0, 1) if tot_grani_kg > 0 else round(vol_target * 0.7, 1)
    assorbimento_grani = round(tot_grani_kg * 1.0, 1)
    litri_pre_boil = round(vol_target * 1.25, 1)
    litri_sparge = round(max(0, litri_pre_boil - (litri_mash - assorbimento_grani)), 1)
    tot_acqua = round(litri_mash + litri_sparge, 1)

    return templates.TemplateResponse(
        request,
        "scheda_cotta.html",
        {
            "cotta": cotta,
            "ricetta": ricetta,
            "vol_target": vol_target,
            "grani": grani,
            "tot_grani_kg": tot_grani_kg,
            "luppoli": luppoli,
            "lieviti": lieviti,
            "misc": misc,
            "mash_steps": mash_steps,
            "stats": stats,
            "litri_mash": litri_mash,
            "litri_sparge": litri_sparge,
            "litri_pre_boil": litri_pre_boil,
            "tot_acqua": tot_acqua,
            "oggi": date.today().strftime("%Y-%m-%d"),
            "session": request.session,
        }
    )
