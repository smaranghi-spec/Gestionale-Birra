import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import (
    Cotta,
    LogCotta,
    Ricetta,
    STATI_COTTA,
    Degustazione,
    InventarioItem,
    IngredienteRicetta,
    CottaIngredienteLotto,
)
from ..codici import genera_prossimo_codice_cotta

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
    avvia_subito: str = Form("0"),
    scarica_magazzino: str = Form("0"),
    volume_batch: Optional[float] = Form(None),
    db: Session = Depends(get_db),
):
    c_codice = codice.strip().upper() if codice and codice.strip() else genera_prossimo_codice_cotta(date.today().year, db)
    stato_iniziale = "brewday" if avvia_subito == "1" else "pianificata"
    data_effettiva = data_brew or (date.today().isoformat() if avvia_subito == "1" else None)

    ricetta_obj = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first() if ricetta_id else None
    vol_ricetta = (ricetta_obj.volume_target_litri or 20.0) if ricetta_obj else 20.0
    vol_effettivo = volume_batch if (volume_batch and volume_batch > 0) else vol_ricetta

    cotta = Cotta(
        nome=nome,
        codice=c_codice,
        ricetta_id=ricetta_id if ricetta_id else None,
        data_brew=data_effettiva,
        fermentatore=fermentatore or None,
        note=note or None,
        stato=stato_iniziale,
        volume_post_bollitura=vol_effettivo if ricetta_obj else None,
        checklist_json="{}",
    )
    db.add(cotta)
    db.flush()

    db.add(
        LogCotta(
            cotta_id=cotta.id,
            timestamp=_now_str(),
            fase=stato_iniziale,
            tipo="evento",
            descrizione=f"Cotta creata ({FASI_LABEL.get(stato_iniziale, stato_iniziale)})",
        )
    )

    # Se collegata a una ricetta e avviata in modalità rapida, pre-assegna automaticamente i lotti FEFO
    if ricetta_obj and avvia_subito == "1":
        fattore = vol_effettivo / vol_ricetta if vol_ricetta else 1.0
        for ing in ricetta_obj.ingredienti:
            qty_scalata = round((ing.quantita or 0.0) * fattore, 3)
            inv_query = db.query(InventarioItem)
            if ing.codice_ingrediente:
                inv_query = inv_query.filter(
                    (InventarioItem.codice_ingrediente == ing.codice_ingrediente) |
                    (InventarioItem.codice == ing.codice_ingrediente) |
                    (InventarioItem.nome.ilike(f"%{ing.nome[:15]}%"))
                )
            else:
                inv_query = inv_query.filter(InventarioItem.nome.ilike(f"%{ing.nome[:15]}%"))

            lotti_db = inv_query.order_by(
                InventarioItem.data_scadenza.asc().nullslast(),
                InventarioItem.id.asc()
            ).all()

            inv_item = None
            for l in lotti_db:
                if (l.quantita or 0.0) >= qty_scalata:
                    inv_item = l
                    break
            if not inv_item and lotti_db:
                inv_item = next((l for l in lotti_db if (l.quantita or 0.0) > 0), lotti_db[0])

            if inv_item and scarica_magazzino == "1":
                inv_item.quantita = max(0.0, round((inv_item.quantita or 0.0) - qty_scalata, 4))
                inv_item.ultimo_aggiornamento = _now_str()

            db.add(CottaIngredienteLotto(
                cotta_id=cotta.id,
                inventario_id=inv_item.id if inv_item else None,
                codice_ingrediente=ing.codice_ingrediente or (inv_item.codice_ingrediente if inv_item else None) or (inv_item.codice if inv_item else None),
                nome_ingrediente=ing.nome,
                categoria=ing.categoria,
                numero_lotto=inv_item.numero_lotto if inv_item else ing.numero_lotto,
                fornitore=inv_item.fornitore if inv_item else ing.fornitore_lotto,
                data_scadenza=inv_item.data_scadenza if inv_item else ing.data_scadenza_lotto,
                quantita_usata=qty_scalata,
                unita=ing.unita,
                timestamp=_now_str(),
                note=f"Auto-FEFO cotta {c_codice}",
            ))

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
    stats_target = {}
    tot_grani_kg = 0.0
    litri_mash = 0.0
    litri_sparge = 0.0
    litri_pre_boil = 0.0
    vol_target = 20.0

    if cotta.ricetta:
        vol_target = cotta.ricetta.volume_target_litri or 20.0
        for ing in cotta.ricetta.ingredienti:
            cat = (ing.categoria or "").lower()
            if cat in ("yeast", "lievito") and ing.attenuation and not attenuation:
                attenuation = ing.attenuation
            if cat in ("grain", "fermentabile", "malto"):
                q = ing.quantita or 0.0
                u = (ing.unita or "kg").lower()
                tot_grani_kg += (q * 0.001) if u in ("g", "gr") else q
        try:
            from ..stats import calcola_stats
            stats_target = calcola_stats(cotta.ricetta, cotta.ricetta.ingredienti)
            litri_mash = stats_target.get("acqua_mash_l") or round(tot_grani_kg * 3.0, 1)
            litri_sparge = stats_target.get("acqua_sparge_l") or round(max(0.0, vol_target * 1.25 - (litri_mash - tot_grani_kg * 0.96)), 1)
            litri_pre_boil = stats_target.get("volume_pre_boil_l") or round(vol_target + 3.5, 1)
        except Exception:
            litri_mash = round(tot_grani_kg * 3.0, 1)
            litri_pre_boil = round(vol_target * 1.2, 1)
            litri_sparge = round(max(0.0, litri_pre_boil - (litri_mash - tot_grani_kg)), 1)

    fg_stimata = None
    if cotta.og_reale and attenuation:
        fg_stimata = round(1 + (cotta.og_reale - 1) * (1 - attenuation / 100), 3)
    elif stats_target.get("fg") and stats_target.get("fg") != "—":
        try:
            fg_stimata = float(stats_target["fg"])
        except Exception:
            pass

    abv_calcolato = None
    if cotta.og_reale and cotta.fg_reale:
        abv_calcolato = round((cotta.og_reale - cotta.fg_reale) * 131.25, 1)
    elif cotta.og_reale and fg_stimata:
        abv_calcolato = round((cotta.og_reale - fg_stimata) * 131.25, 1)

    # Calcolo Pitch Rate consigliato stile BeerSmith (cellule e grammi lievito secco)
    og_ref = cotta.og_reale or (float(stats_target["og"]) if stats_target.get("og") and stats_target.get("og") != "—" else 1.050)
    vol_ref = cotta.volume_post_bollitura or vol_target
    plato_ref = max(1.0, (og_ref - 1.0) * 1000.0 / 4.0)
    cellule_miliardi = round(0.75 * vol_ref * plato_ref)
    grammi_lievito_secco = round(cellule_miliardi / 10.0, 1)

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

    # Procedure Operative Standard (SOP) e stato checklist cotta
    from .procedure import get_sops_parsed
    sops = get_sops_parsed(db)
    try:
        checklist_state = json.loads(cotta.checklist_json or "{}")
    except Exception:
        checklist_state = {}

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
            "stats_target": stats_target,
            "tot_grani_kg": round(tot_grani_kg, 2),
            "litri_mash": litri_mash,
            "litri_sparge": litri_sparge,
            "litri_pre_boil": litri_pre_boil,
            "vol_target": vol_target,
            "cellule_miliardi": cellule_miliardi,
            "grammi_lievito_secco": grammi_lievito_secco,
            "sops": sops,
            "checklist_state": checklist_state,
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

        if prossimo == "brewday" and not cotta.data_brew:
            cotta.data_brew = date.today().isoformat()
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


@router.post("/cotte/{cotta_id}/stato")
def imposta_stato(cotta_id: int, nuovo_stato: str = Form(...), db: Session = Depends(get_db)):
    """Cambio stato rapido con 1 click direttamente sulla barra pipeline."""
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta or nuovo_stato not in STATI_COTTA:
        return RedirectResponse(f"/cotte/{cotta_id}", status_code=303)

    if cotta.stato != nuovo_stato:
        vecchio = cotta.stato
        cotta.stato = nuovo_stato
        if nuovo_stato == "brewday" and not cotta.data_brew:
            cotta.data_brew = date.today().isoformat()
        elif nuovo_stato == "fermentazione" and not cotta.data_inoculo:
            cotta.data_inoculo = date.today().isoformat()
        elif nuovo_stato == "imbottigliamento" and not cotta.data_imbottigliamento:
            cotta.data_imbottigliamento = date.today().isoformat()

        db.add(
            LogCotta(
                cotta_id=cotta_id,
                timestamp=_now_str(),
                fase=nuovo_stato,
                tipo="avanzamento",
                descrizione=f"Cambio fase: {FASI_LABEL.get(vecchio, vecchio)} → {FASI_LABEL.get(nuovo_stato, nuovo_stato)}",
            )
        )
        db.commit()

    return RedirectResponse(f"/cotte/{cotta_id}", status_code=303)


@router.post("/cotte/{cotta_id}/checklist")
async def aggiorna_checklist_cotta(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    """Salva lo stato delle checklist SOP spuntate durante la lavorazione della cotta."""
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return {"ok": False}

    try:
        payload = await request.json()
        key = payload.get("key")
        checked = bool(payload.get("checked"))
        label = payload.get("label", "")
        state = json.loads(cotta.checklist_json or "{}")
        if key:
            state[key] = checked
            cotta.checklist_json = json.dumps(state, ensure_ascii=False)
            if checked and label:
                db.add(LogCotta(
                    cotta_id=cotta_id,
                    timestamp=_now_str(),
                    fase=cotta.stato,
                    tipo="evento",
                    descrizione=f"✓ SOP completato: {label}",
                ))
            db.commit()
        return {"ok": True, "state": state}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


def _parse_float(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(val: Optional[str]) -> Optional[int]:
    f = _parse_float(val)
    return int(round(f)) if f is not None else None


@router.post("/cotte/{cotta_id}/aggiorna")
async def aggiorna_cotta(
    cotta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    form = await request.form()

    float_fields = [
        "volume_pre_bollitura", "volume_post_bollitura", "ph_mash", "ph_pre_bollitura",
        "temp_mash_gradi", "efficienza_reale", "og_reale", "fg_reale", "temp_fermentazione",
        "temp_secondaria", "volume_imbottigliato", "carbonatazione_vols", "priming_sugar_g",
        "temp_ambiente", "acqua_totale_litri", "pressione_bar",
    ]
    int_fields = ["durata_bollitura_min"]
    str_fields = [
        "fermentatore", "data_brew", "data_inoculo", "data_travasamento", "data_imbottigliamento",
        "tipo_packaging", "colore_visivo", "limpidezza", "note", "note_ferm", "note_cond",
        "note_imbott", "codice",
    ]

    for k in float_fields:
        if k in form:
            val = _parse_float(form.get(k))
            if val is not None:
                setattr(cotta, k, val)

    for k in int_fields:
        if k in form:
            val = _parse_int(form.get(k))
            if val is not None:
                setattr(cotta, k, val)

    for k in str_fields:
        if k in form:
            val = form.get(k)
            if val is not None and str(val).strip() != "":
                setattr(cotta, k, str(val).strip())

    # Calcolo automatico Efficienza Reale (stile BeerSmith) se OG Reale e Volume Post-Bollitura sono presenti
    if cotta.og_reale and cotta.volume_post_bollitura and cotta.ricetta and not _parse_float(form.get("efficienza_reale")):
        punti_potenziali_tot = 0.0
        for ing in cotta.ricetta.ingredienti:
            if (ing.categoria or "").lower() in ("grain", "fermentabile", "malto"):
                q_kg = (ing.quantita or 0.0) * (0.001 if (ing.unita or "").lower() in ("g", "gr") else 1.0)
                resa = (ing.yield_percent or 78.0) / 100.0
                # 384 punti litro/kg per saccarosio 100%
                punti_potenziali_tot += q_kg * 384.0 * resa
        if punti_potenziali_tot > 0:
            punti_ottenuti = (cotta.og_reale - 1.0) * 1000.0 * cotta.volume_post_bollitura
            cotta.efficienza_reale = round((punti_ottenuti / punti_potenziali_tot) * 100.0, 1)

    if cotta.og_reale and cotta.fg_reale:
        cotta.abv_reale = round((cotta.og_reale - cotta.fg_reale) * 131.25, 1)

    db.commit()
    tab = form.get("tab_attiva", "")
    suffix = f"?tab={tab}" if tab else ""
    return RedirectResponse(f"/cotte/{cotta_id}{suffix}", status_code=303)


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

        # Cerca lotti in magazzino per codice_ingrediente o per nome
        inv_query = db.query(InventarioItem)
        if ing.codice_ingrediente:
            inv_query = inv_query.filter(
                (InventarioItem.codice_ingrediente == ing.codice_ingrediente) |
                (InventarioItem.codice == ing.codice_ingrediente) |
                (InventarioItem.nome.ilike(f"%{ing.nome[:15]}%"))
            )
        else:
            inv_query = inv_query.filter(
                InventarioItem.nome.ilike(f"%{ing.nome[:15]}%")
            )

        # Ordina per FEFO (data di scadenza più vicina prima)
        lotti_db = inv_query.order_by(
            InventarioItem.data_scadenza.asc().nullslast(),
            InventarioItem.id.asc()
        ).all()

        totale_disponibile = sum((l.quantita or 0.0) for l in lotti_db) if lotti_db else 0.0

        # Identifica il lotto consigliato (FEFO con giacenza > 0)
        lotto_selezionato_id = None
        for l in lotti_db:
            if (l.quantita or 0.0) >= qty_scalata:
                lotto_selezionato_id = l.id
                break
        if not lotto_selezionato_id and lotti_db:
            for l in lotti_db:
                if (l.quantita or 0.0) > 0:
                    lotto_selezionato_id = l.id
                    break
        if not lotto_selezionato_id and lotti_db:
            lotto_selezionato_id = lotti_db[0].id

        ingredienti_scalati.append({
            "id": ing.id,
            "nome": ing.nome,
            "codice_ingrediente": ing.codice_ingrediente,
            "categoria": ing.categoria,
            "quantita_ricetta": ing.quantita,
            "unita": ing.unita,
            "quantita_scalata": qty_scalata,
            "disponibile": round(totale_disponibile, 3) if lotti_db else None,
            "sufficiente": (not lotti_db or totale_disponibile >= qty_scalata),
            "lotti": lotti_db,
            "lotto_default_id": lotto_selezionato_id,
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

    # Assicura codice cotta univoco (COT-YYYY-NNN)
    if not cotta.codice:
        cotta.codice = genera_prossimo_codice_cotta(date.today().year, db)

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
            descrizione=f"Avviata produzione — batch {cotta.codice} — volume: {vol_batch}L (fattore scala: ×{round(fattore,3)})",
        ))

    # Pulisci eventuali precedenti registrazioni lotti se ri-eseguita
    db.query(CottaIngredienteLotto).filter(CottaIngredienteLotto.cotta_id == cotta_id).delete(synchronize_session=False)

    movimenti = []
    for ing in ricetta.ingredienti:
        qty_scalata = round(ing.quantita * fattore, 3)
        lotto_sel = (form.get(f"lotto_sel_{ing.id}") or "").strip()
        lotto_manuale = (form.get(f"lotto_manuale_{ing.id}") or "").strip()
        fornitore_manuale = (form.get(f"fornitore_manuale_{ing.id}") or "").strip()
        scadenza_manuale = (form.get(f"scadenza_manuale_{ing.id}") or "").strip()

        inv_item = None
        if lotto_sel and lotto_sel.isdigit():
            inv_item = db.query(InventarioItem).filter(InventarioItem.id == int(lotto_sel)).first()

        num_lotto = None
        fornitore = None
        data_scad = None
        inv_id = None

        if inv_item:
            inv_id = inv_item.id
            num_lotto = inv_item.numero_lotto
            fornitore = inv_item.fornitore
            data_scad = inv_item.data_scadenza
            if scarica_inventario:
                inv_item.quantita = max(0.0, round((inv_item.quantita or 0.0) - qty_scalata, 4))
                inv_item.ultimo_aggiornamento = _now_str()
        elif lotto_manuale:
            num_lotto = lotto_manuale
            fornitore = fornitore_manuale or None
            data_scad = scadenza_manuale or None

        # Crea record tracciabilità cotta-lotto
        c_lotto = CottaIngredienteLotto(
            cotta_id=cotta_id,
            inventario_id=inv_id,
            codice_ingrediente=ing.codice_ingrediente or (inv_item.codice_ingrediente if inv_item else None) or (inv_item.codice if inv_item else None),
            nome_ingrediente=ing.nome,
            categoria=ing.categoria,
            numero_lotto=num_lotto,
            fornitore=fornitore,
            data_scadenza=data_scad,
            quantita_usata=qty_scalata,
            unita=ing.unita,
            timestamp=_now_str(),
            note=f"Tracciabilità cotta {cotta.codice}",
        )
        db.add(c_lotto)

        log_d = f"{ing.nome} × {qty_scalata} {ing.unita}"
        if num_lotto:
            log_d += f" (Lotto: {num_lotto})"
        movimenti.append(log_d)

    if movimenti:
        db.add(LogCotta(
            cotta_id=cotta_id,
            timestamp=_now_str(),
            fase="brewday",
            tipo="nota",
            descrizione="Materie prime impiegate: " + " | ".join(movimenti[:5]) + (f" + altri {len(movimenti)-5}" if len(movimenti)>5 else ""),
        ))

    db.commit()
    return RedirectResponse(f"/cotte/{cotta_id}?msg=Produzione+avviata+e+lotti+registrati", status_code=303)


@router.post("/cotte/{cotta_id}/elimina")
def elimina_cotta(cotta_id: int, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if cotta:
        try:
            from ..models import LetturaDensita, LogCotta, Degustazione, AggiuntaCotta, CottaIngredienteLotto
            db.query(CottaIngredienteLotto).filter(CottaIngredienteLotto.cotta_id == cotta_id).delete(synchronize_session=False)
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
    return templates.TemplateResponse(request, "degustazioni.html", {
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


@router.get("/cotte/{cotta_id}/brew-day", response_class=HTMLResponse)
def brew_day_view(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return RedirectResponse("/cotte", status_code=303)

    ricetta = db.query(Ricetta).filter(Ricetta.id == cotta.ricetta_id).first() if cotta.ricetta_id else None
    ingredienti = []
    if ricetta:
        ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta.id).all()

    grani = [i for i in ingredienti if i.categoria == "grain"]
    luppoli = sorted([i for i in ingredienti if i.categoria == "hop"], key=lambda x: (x.time_min or 0), reverse=True)
    lieviti = [i for i in ingredienti if i.categoria == "yeast"]
    altri = [i for i in ingredienti if i.categoria not in ("grain", "hop", "yeast")]

    stats = {}
    if ricetta:
        from ..stats import calcola_stats
        stats = calcola_stats(ricetta, ingredienti)

    mash_steps = []
    if ricetta and ricetta.profilo_mash and ricetta.profilo_mash.steps_json:
        try:
            mash_steps = json.loads(ricetta.profilo_mash.steps_json)
        except Exception:
            mash_steps = []
    if not mash_steps:
        mash_steps = [
            {"nome": "Saccarificazione (Infuso Singolo)", "temp_gradi": 67, "durata_min": 60},
            {"nome": "Mash Out", "temp_gradi": 78, "durata_min": 10},
        ]

    return templates.TemplateResponse(
        request,
        "brew_day.html",
        {
            "cotta": cotta,
            "ricetta": ricetta,
            "grani": grani,
            "luppoli": luppoli,
            "lieviti": lieviti,
            "altri": altri,
            "stats": stats,
            "mash_steps": mash_steps,
            "session": request.session,
        }
    )

