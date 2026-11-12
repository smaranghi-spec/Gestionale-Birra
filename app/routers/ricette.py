import json
from typing import Optional
from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from ..db import SessionLocal
from ..models import (
    Ricetta,
    IngredienteRicetta,
    Stile,
    Cotta,
    LogCotta,
    ProfiloAcqua,
    ProfiloAmmostamento,
    ProfiloAcquaPreset,
    CatalogoIngrediente,
    InventarioItem,
    ProfiloBirrificio,
)
from ..stats import (
    calcola_stats,
    confronta_stile,
    calcola_percentuali,
    calcola_costo,
    srm_to_hex,
)
from ..codici import genera_prossimo_codice_ricetta, genera_prossimo_codice_cotta
from ..mash_templates import MASH_TEMPLATES, MASH_TEMPLATES_ALIASES, get_template_steps

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["srm_to_hex"] = srm_to_hex


def _parse_temp(val, default=67.0) -> float:
    if val is None:
        return default
    s = str(val).replace(",", ".").strip()
    try:
        f = float(s)
        return round(f, 1)
    except (ValueError, TypeError):
        return default


def _parse_durata(val, default=60) -> int:
    if val is None:
        return default
    s = str(val).replace(",", ".").strip().split(".")[0]
    digits = "".join(c for c in s if c.isdigit())
    try:
        return max(1, int(digits)) if digits else default
    except (ValueError, TypeError):
        return default


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _calcola_fattibilita_ricetta(ingredienti_ric: list, inv_items: list) -> dict:
    """Confronta gli ingredienti della ricetta con le scorte in magazzino e rileva differenze di AA% sui luppoli."""
    dettaglio = {}
    mancanti = []
    hop_aa_diffs = []

    for ing in ingredienti_ric:
        req_qty = float(ing.quantita or 0.0)
        req_unit = (ing.unita or "kg").strip().lower()
        cname = (ing.nome or "").strip().lower()
        csku = (ing.codice_ingrediente or "").strip().upper()

        matches = []
        for inv in inv_items:
            inv_sku = (inv.codice_ingrediente or inv.codice or "").strip().upper()
            inv_name = (inv.nome or "").strip().lower()
            if (csku and inv_sku == csku) or (cname and (cname == inv_name or cname in inv_name or inv_name in cname)):
                matches.append(inv)

        disp_in_req_unit = 0.0
        best_aa = None
        best_lotto = None
        for m in matches:
            mq = float(m.quantita or 0.0)
            mu = (m.unita or "kg").strip().lower()
            if mu == req_unit:
                disp_in_req_unit += mq
            elif mu == "kg" and req_unit == "g":
                disp_in_req_unit += mq * 1000.0
            elif mu == "g" and req_unit == "kg":
                disp_in_req_unit += mq / 1000.0
            elif mu == "l" and req_unit == "ml":
                disp_in_req_unit += mq * 1000.0
            elif mu == "ml" and req_unit == "l":
                disp_in_req_unit += mq / 1000.0
            else:
                disp_in_req_unit += mq
            if mq > 0 and m.alfa_acidi and best_aa is None:
                best_aa = float(m.alfa_acidi)
                best_lotto = m.numero_lotto

        disp_in_req_unit = round(disp_in_req_unit, 3)
        ok = disp_in_req_unit >= req_qty if req_qty > 0 else True
        manca_qty = round(max(0.0, req_qty - disp_in_req_unit), 3)
        if not ok:
            mancanti.append({
                "id": ing.id,
                "nome": ing.nome,
                "categoria": ing.categoria,
                "richiesto": req_qty,
                "disponibile": disp_in_req_unit,
                "manca": manca_qty,
                "unita": ing.unita or "kg",
            })

        qty_aa_adj = None
        if ing.categoria == "hop" and best_aa and best_aa > 0 and ing.alpha_acid and abs(best_aa - float(ing.alpha_acid)) >= 0.2:
            qty_aa_adj = round(req_qty * (float(ing.alpha_acid) / best_aa), 1)
            hop_aa_diffs.append({
                "id": ing.id,
                "nome": ing.nome,
                "aa_ricetta": ing.alpha_acid,
                "aa_lotto": best_aa,
                "lotto": best_lotto,
                "qty_attuale": req_qty,
                "qty_consigliata": qty_aa_adj,
                "unita": ing.unita or "g",
            })

        dettaglio[ing.id] = {
            "disp": disp_in_req_unit,
            "ok": ok,
            "manca": manca_qty,
            "aa_lotto": best_aa,
            "lotto": best_lotto,
            "qty_aa_adj": qty_aa_adj,
        }

    return {
        "pronta": len(ingredienti_ric) > 0 and len(mancanti) == 0,
        "tot_ing": len(ingredienti_ric),
        "n_mancanti": len(mancanti),
        "mancanti": mancanti,
        "hop_aa_diffs": hop_aa_diffs,
        "dettaglio": dettaglio,
    }


@router.get("/ricette")
def redirect_ricette():
    return RedirectResponse("/ricette/html", status_code=303)


@router.get("/ricette/html", response_class=HTMLResponse)
def lista_ricette(request: Request, db: Session = Depends(get_db)):
    ricette = db.query(Ricetta).all()
    stili = db.query(Stile).order_by(Stile.linea_guida, Stile.nome).all()
    profili_preset = db.query(ProfiloAcquaPreset).order_by(ProfiloAcquaPreset.nome).all()
    inv_items = db.query(InventarioItem).all()

    counts_q = (
        db.query(Cotta.ricetta_id, func.count(Cotta.id))
        .group_by(Cotta.ricetta_id)
        .all()
    )
    cotte_count = {rid: cnt for rid, cnt in counts_q if rid is not None}

    fattibilita_map = {}
    for r in ricette:
        fattibilita_map[r.id] = _calcola_fattibilita_ricetta(r.ingredienti or [], inv_items)

    return templates.TemplateResponse(
        request,
        "ricette.html",
        {
            "request": request,
            "ricette": ricette,
            "stili": stili,
            "profili_preset": profili_preset,
            "cotte_count": cotte_count,
            "fattibilita_map": fattibilita_map,
            "mash_templates": MASH_TEMPLATES,
        },
    )


@router.post("/ricette/html")
def crea_ricetta(
    nome: str = Form(...),
    codice: str = Form(""),
    tipo: str = Form(...),
    volume_target_litri: float = Form(...),
    efficienza: float = Form(...),
    versione: int = Form(...),
    stile_id: int = Form(0),
    note: str = Form(""),
    profilo_acqua_preset_id: int = Form(0),
    tipo_mash: str = Form(""),
    db: Session = Depends(get_db),
):
    import json as _json
    c_codice = codice.strip().upper() if codice and codice.strip() else genera_prossimo_codice_ricetta(db)
    r = Ricetta(
        codice=c_codice,
        nome=nome,
        tipo=tipo,
        volume_target_litri=volume_target_litri,
        efficienza=efficienza,
        versione=versione,
        stile_id=stile_id if stile_id != 0 else None,
        note=note or None,
    )
    db.add(r)
    db.flush()

    if profilo_acqua_preset_id:
        preset = db.query(ProfiloAcquaPreset).filter(ProfiloAcquaPreset.id == profilo_acqua_preset_id).first()
        if preset:
            pa = ProfiloAcqua(
                ricetta_id=r.id,
                nome=preset.nome,
                ca=preset.ca, mg=preset.mg, na=preset.na,
                cl=preset.cl, so4=preset.so4, hco3=preset.hco3,
            )
            db.add(pa)

    if tipo_mash:
        t_steps = get_template_steps(tipo_mash)
        if t_steps:
            nome_clean = MASH_TEMPLATES_ALIASES.get(tipo_mash, tipo_mash)
            pm = ProfiloAmmostamento(
                ricetta_id=r.id,
                nome=nome_clean,
                steps_json=_json.dumps(t_steps, ensure_ascii=False),
            )
            db.add(pm)

    try:
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/ricette/html?msg=Errore+creazione+ricetta", status_code=303)
    return RedirectResponse(f"/ricette/{r.id}", status_code=303)


# ── LIBRERIA RICETTE PREDEFINITE ──────────────────────────────────────────────

@router.get("/ricette/libreria", response_class=HTMLResponse)
def libreria_ricette_view(
    request: Request,
    categoria: str = "",
    q: str = "",
    db: Session = Depends(get_db),
):
    from ..data_ricette import get_ricette_libreria
    tutte_ricette = get_ricette_libreria()

    categorie = [
        "Tutte",
        "Luppolate (IPA & Pale Ale)",
        "Lager & Bassa Fermentazione",
        "Belghe & Saison",
        "Frumento & Weizen",
        "Scure (Stout & Porter)",
        "Classiche UK & Tedesche",
    ]

    filtered = tutte_ricette
    if categoria and categoria != "Tutte":
        filtered = [r for r in filtered if r.get("categoria_macro") == categoria]

    if q and q.strip():
        term = q.strip().lower()
        filtered = [
            r for r in filtered
            if term in (r.get("nome") or "").lower()
            or term in (r.get("stile_nome") or "").lower()
            or term in (r.get("stile_bjcp") or "").lower()
            or term in (r.get("descrizione") or "").lower()
            or any(term in (i.get("nome") or "").lower() for i in r.get("ingredienti", []))
        ]

    return templates.TemplateResponse(
        request,
        "libreria_ricette.html",
        {
            "request": request,
            "ricette": filtered,
            "totale": len(filtered),
            "totale_catalogo": len(tutte_ricette),
            "categorie": categorie,
            "categoria_selezionata": categoria or "Tutte",
            "q": q,
        },
    )


@router.get("/ricette/libreria/{slug}/json")
def libreria_ricetta_json(slug: str):
    from ..data_ricette import get_ricetta_by_slug
    r = get_ricetta_by_slug(slug)
    if not r:
        return JSONResponse(status_code=404, content={"error": "Ricetta non trovata"})
    return JSONResponse(content=r)


@router.post("/ricette/libreria/importa/{slug}")
def libreria_importa_ricetta(slug: str, request: Request, db: Session = Depends(get_db)):
    from ..data_ricette import get_ricetta_by_slug
    r_data = get_ricetta_by_slug(slug)
    if not r_data:
        return RedirectResponse("/ricette/libreria?error=Ricetta+non+trovata", status_code=303)

    try:
        # Match BJCP style in DB if exists
        stile_obj = None
        if r_data.get("stile_bjcp"):
            stile_obj = db.query(Stile).filter(
                (Stile.linea_guida.ilike(f"%{r_data['stile_bjcp']}%")) | (Stile.nome.ilike(f"%{r_data['stile_bjcp']}%"))
            ).first()
        if not stile_obj and r_data.get("stile_nome"):
            stile_obj = db.query(Stile).filter(Stile.nome.ilike(f"%{r_data['stile_nome']}%")).first()

        note_content = (
            f"{r_data.get('descrizione', '')}\n\n[Consigli Brewday]: {r_data.get('consigli_brewday', '')}"
        ).strip()

        c_codice = genera_prossimo_codice_ricetta(db)
        nuova_ricetta = Ricetta(
            codice=c_codice,
            nome=r_data["nome"],
            tipo=r_data.get("tipo", "All Grain"),
            volume_target_litri=float(r_data.get("volume_target_litri", 23.0)),
            efficienza=float(r_data.get("efficienza", 75.0)),
            versione=1,
            stile_id=stile_obj.id if stile_obj else None,
            note=note_content,
            pubblica=False,
        )
        db.add(nuova_ricetta)
        db.flush()

        # Add ingredients
        for ing in r_data.get("ingredienti", []):
            ing_nome = ing.get("nome")
            cat_match = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.nome.ilike(f"%{ing_nome[:15]}%")).first() if ing_nome else None
            sku = cat_match.codice if cat_match else None
            db.add(
                IngredienteRicetta(
                    ricetta_id=nuova_ricetta.id,
                    codice_ingrediente=sku,
                    nome=ing_nome,
                    categoria=ing.get("categoria"),
                    quantita=float(ing.get("quantita", 0.0)),
                    unita=ing.get("unita", "kg"),
                    note=ing.get("note"),
                    time_min=ing.get("time_min"),
                    fermentable_type=ing.get("fermentable_type"),
                    yield_percent=float(ing["yield_percent"]) if ing.get("yield_percent") is not None else None,
                    color_srm=float(ing["color_srm"]) if ing.get("color_srm") is not None else None,
                    alpha_acid=float(ing["alpha_acid"]) if ing.get("alpha_acid") is not None else None,
                    hop_use=ing.get("hop_use"),
                    hop_form=ing.get("hop_form"),
                    attenuation=float(ing["attenuation"]) if ing.get("attenuation") is not None else None,
                    yeast_type=ing.get("yeast_type"),
                    yeast_form=ing.get("yeast_form"),
                    misc_type=ing.get("misc_type"),
                    misc_use=ing.get("misc_use"),
                )
            )

        # Add mash profile
        mash_data = r_data.get("profilo_mash")
        if mash_data:
            steps_list = mash_data.get("steps", [])
            normalized_steps = []
            for idx, s in enumerate(steps_list, start=1):
                normalized_steps.append({
                    "step_order": s.get("step_order", idx),
                    "nome": s.get("name") or s.get("nome", f"Step {idx}"),
                    "temp_gradi": s.get("step_temp") or s.get("temp", 67),
                    "durata_min": s.get("step_time") or s.get("durata", 60),
                    "tipo": s.get("step_type") or s.get("tipo", "Infusion"),
                })
            db.add(
                ProfiloAmmostamento(
                    ricetta_id=nuova_ricetta.id,
                    nome=mash_data.get("nome", "Profilo Ammostamento"),
                    steps_json=json.dumps(normalized_steps, ensure_ascii=False),
                )
            )

        # Add water profile
        water_data = r_data.get("profilo_acqua")
        if water_data:
            db.add(
                ProfiloAcqua(
                    ricetta_id=nuova_ricetta.id,
                    nome=water_data.get("nome", "Profilo Acqua"),
                    ca=float(water_data.get("ca", 0.0)),
                    mg=float(water_data.get("mg", 0.0)),
                    na=float(water_data.get("na", 0.0)),
                    cl=float(water_data.get("cl", 0.0)),
                    so4=float(water_data.get("so4", 0.0)),
                    hco3=float(water_data.get("hco3", 0.0)),
                )
            )

        db.commit()
        return RedirectResponse(
            f"/ricette/{nuova_ricetta.id}?imported=true&msg=Ricetta+aggiunta+con+successo+alle+tue+ricette!",
            status_code=303,
        )
    except Exception as e:
        db.rollback()
        import urllib.parse
        err_msg = urllib.parse.quote(f"Errore durante l'importazione: {str(e)}")
        return RedirectResponse(f"/ricette/libreria?error={err_msg}", status_code=303)


@router.get("/ricette/{ricetta_id}", response_class=HTMLResponse)
def dettaglio_ricetta(ricetta_id: int, request: Request, db: Session = Depends(get_db)):
    from datetime import date

    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return HTMLResponse("Ricetta non trovata", status_code=404)

    ingredienti = (
        db.query(IngredienteRicetta)
        .filter(IngredienteRicetta.ricetta_id == ricetta_id)
        .all()
    )
    stili = db.query(Stile).all()
    stats = calcola_stats(ricetta, ingredienti)
    stile_corrente = (
        db.query(Stile).filter(Stile.id == ricetta.stile_id).first()
        if ricetta.stile_id
        else None
    )
    cf = confronta_stile(stats, stile_corrente)
    percentuali = calcola_percentuali(ingredienti)
    costo = calcola_costo(ingredienti)
    srm_hex = srm_to_hex(stats["srm"])

    cotte = (
        db.query(Cotta)
        .filter(Cotta.ricetta_id == ricetta_id)
        .order_by(Cotta.id.desc())
        .all()
    )
    n_cotte = len(cotte)

    profilo_acqua = (
        db.query(ProfiloAcqua).filter(ProfiloAcqua.ricetta_id == ricetta_id).first()
    )
    profilo_mash = (
        db.query(ProfiloAmmostamento)
        .filter(ProfiloAmmostamento.ricetta_id == ricetta_id)
        .first()
    )

    mash_steps = []
    if profilo_mash and profilo_mash.steps_json:
        try:
            parsed = json.loads(profilo_mash.steps_json)
            mash_steps = parsed if isinstance(parsed, list) else []
        except Exception:
            mash_steps = []

    mash_totale_minuti = sum(s.get("durata_min", 0) for s in mash_steps)
    sac_temps = [s.get("temp_gradi", 67.0) for s in mash_steps if "sacc" in s.get("nome", "").lower() or (60.0 <= s.get("temp_gradi", 0) <= 72.0)]
    sac_temp_media = round(sum(sac_temps) / len(sac_temps), 1) if sac_temps else (mash_steps[0].get("temp_gradi", 67.0) if mash_steps else 67.0)

    profili_preset_acqua = db.query(ProfiloAcquaPreset).order_by(ProfiloAcquaPreset.nome).all()
    catalogo_items = db.query(CatalogoIngrediente).order_by(CatalogoIngrediente.categoria, CatalogoIngrediente.nome).all()
    inventario_items = db.query(InventarioItem).order_by(InventarioItem.categoria, InventarioItem.nome).all()
    profili_impianto = db.query(ProfiloBirrificio).order_by(ProfiloBirrificio.nome).all()

    fermentazione_steps = []
    if ricetta.profilo_fermentazione_json:
        try:
            parsed_ferm = json.loads(ricetta.profilo_fermentazione_json)
            fermentazione_steps = parsed_ferm if isinstance(parsed_ferm, list) else []
        except Exception:
            fermentazione_steps = []

    fattibilita = _calcola_fattibilita_ricetta(ingredienti, inventario_items)

    return templates.TemplateResponse(
        request,
        "dettaglio_ricetta.html",
        {
            "request": request,
            "ricetta": ricetta,
            "ingredienti": ingredienti,
            "stili": stili,
            "stats": stats,
            "stile_corrente": stile_corrente,
            "confronto_stile": cf,
            "percentuali": percentuali,
            "costo": costo,
            "srm_hex": srm_hex,
            "cotte": cotte,
            "n_cotte": n_cotte,
            "oggi": date.today().isoformat(),
            "profilo_acqua": profilo_acqua,
            "profilo_mash": profilo_mash,
            "mash_steps": mash_steps,
            "mash_steps_json": json.dumps(mash_steps, ensure_ascii=False),
            "mash_templates": MASH_TEMPLATES,
            "mash_templates_json": json.dumps(MASH_TEMPLATES, ensure_ascii=False),
            "mash_totale_minuti": mash_totale_minuti,
            "sac_temp_media": sac_temp_media,
            "profili_preset_acqua": profili_preset_acqua,
            "catalogo_items": catalogo_items,
            "inventario_items": inventario_items,
            "profili_impianto": profili_impianto,
            "fermentazione_steps": fermentazione_steps,
            "fattibilita": fattibilita,
        },
    )


@router.post("/ricette/{ricetta_id}/aggiungi-ingrediente-rapido")
def aggiungi_ingrediente_rapido(
    ricetta_id: int,
    sorgente: str = Form("catalogo"),
    catalogo_id: int = Form(None),
    inventario_id: int = Form(None),
    nome_manuale: str = Form(None),
    categoria_manuale: str = Form(None),
    quantita: float = Form(...),
    unita: str = Form("kg"),
    time_min: int = Form(None),
    note: str = Form(None),
    param_resa: float = Form(None),
    param_colore: float = Form(None),
    param_alpha: float = Form(None),
    param_atten: float = Form(None),
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    ing = None

    if sorgente == "catalogo" and catalogo_id:
        item = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == catalogo_id).first()
        if item:
            ing = IngredienteRicetta(
                ricetta_id=ricetta_id,
                codice_ingrediente=item.codice,
                nome=item.nome,
                categoria=item.categoria,
                quantita=quantita,
                unita=unita,
                time_min=time_min,
                note=note or None,
                fermentable_type=item.fermentable_type,
                yield_percent=param_resa if param_resa is not None else item.yield_percent,
                color_srm=param_colore if param_colore is not None else item.color_srm,
                alpha_acid=param_alpha if param_alpha is not None else item.alpha_acid,
                hop_use=item.hop_use,
                hop_form=item.hop_form,
                attenuation=param_atten if param_atten is not None else item.attenuation,
                yeast_type=item.yeast_type,
                yeast_form=item.yeast_form,
                misc_type=item.misc_type,
                misc_use=item.misc_use,
            )

    elif sorgente == "inventario" and inventario_id:
        item = db.query(InventarioItem).filter(InventarioItem.id == inventario_id).first()
        if item:
            cat = "misc"
            tipo = (item.tipo_ingrediente or "").lower()
            nome_lower = (item.nome or "").lower()
            if tipo in ("grain", "malto", "fermentabile") or "malto" in nome_lower or "grain" in nome_lower or "flaked" in nome_lower or "pilsner" in nome_lower:
                cat = "grain"
            elif tipo in ("hop", "luppolo") or "luppolo" in nome_lower or "hop" in nome_lower or "pellet" in nome_lower:
                cat = "hop"
            elif tipo in ("yeast", "lievito") or "lievito" in nome_lower or "yeast" in nome_lower:
                cat = "yeast"
            else:
                cat_match = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.nome.ilike(f"%{item.nome[:15]}%")).first()
                if cat_match:
                    cat = cat_match.categoria

            cat_match = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.nome.ilike(f"%{item.nome[:15]}%")).first()
            color_srm = (item.colore_ebc / 1.97) if item.colore_ebc else (cat_match.color_srm if cat_match else (3.0 if cat == "grain" else None))
            yield_pct = item.resa_estratto if item.resa_estratto is not None else (cat_match.yield_percent if cat_match else (75.0 if cat == "grain" else None))
            alpha_acid = item.alfa_acidi if item.alfa_acidi is not None else (cat_match.alpha_acid if cat_match else (5.0 if cat == "hop" else None))
            attenuation = item.attenuazione if item.attenuazione is not None else (cat_match.attenuation if cat_match else (75.0 if cat == "yeast" else None))

            ing = IngredienteRicetta(
                ricetta_id=ricetta_id,
                codice_ingrediente=item.codice_ingrediente or item.codice or (cat_match.codice if cat_match else None),
                nome=item.nome,
                categoria=cat,
                quantita=quantita,
                unita=unita,
                time_min=time_min,
                note=note or None,
                prezzo_unitario=item.prezzo_unitario,
                numero_lotto=item.numero_lotto,
                fornitore_lotto=item.fornitore,
                data_scadenza_lotto=item.data_scadenza,
                fermentable_type=cat_match.fermentable_type if cat_match else ("Grain" if cat == "grain" else None),
                yield_percent=param_resa if param_resa is not None else yield_pct,
                color_srm=param_colore if param_colore is not None else color_srm,
                alpha_acid=param_alpha if param_alpha is not None else alpha_acid,
                hop_use=cat_match.hop_use if cat_match else ("Boil" if cat == "hop" else None),
                hop_form=cat_match.hop_form if cat_match else ("Pellet" if cat == "hop" else None),
                attenuation=param_atten if param_atten is not None else attenuation,
                yeast_type=cat_match.yeast_type if cat_match else ("Ale" if cat == "yeast" else None),
                yeast_form=cat_match.yeast_form if cat_match else ("Secco" if cat == "yeast" else None),
                misc_type=cat_match.misc_type if cat_match else None,
                misc_use=cat_match.misc_use if cat_match else None,
            )

    elif sorgente == "manuale" and nome_manuale and categoria_manuale:
        cat = categoria_manuale.strip().lower()
        cat_match = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.nome.ilike(f"%{nome_manuale.strip()[:15]}%")).first()
        ing = IngredienteRicetta(
            ricetta_id=ricetta_id,
            codice_ingrediente=cat_match.codice if cat_match else None,
            nome=nome_manuale.strip(),
            categoria=cat,
            quantita=quantita,
            unita=unita,
            time_min=time_min,
            note=note or None,
            yield_percent=param_resa if param_resa is not None else (75.0 if cat == "grain" else None),
            color_srm=param_colore if param_colore is not None else (3.0 if cat == "grain" else None),
            alpha_acid=param_alpha if param_alpha is not None else (5.0 if cat == "hop" else None),
            attenuation=param_atten if param_atten is not None else (75.0 if cat == "yeast" else None),
            hop_use="Boil" if cat == "hop" else None,
            hop_form="Pellet" if cat == "hop" else None,
            fermentable_type="Grain" if cat == "grain" else None,
            yeast_form="Secco" if cat == "yeast" else None,
        )

    if ing:
        try:
            db.add(ing)
            db.commit()
        except Exception:
            db.rollback()
            return RedirectResponse(f"/ricette/{ricetta_id}?msg=Errore+nel+salvataggio+dell+ingrediente", status_code=303)

    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.post("/ricette/{ricetta_id}/profilo-acqua")
def salva_profilo_acqua(
    ricetta_id: int,
    nome: str = Form("Custom"),
    ca: float = Form(0.0),
    mg: float = Form(0.0),
    na: float = Form(0.0),
    cl: float = Form(0.0),
    so4: float = Form(0.0),
    hco3: float = Form(0.0),
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    pa = db.query(ProfiloAcqua).filter(ProfiloAcqua.ricetta_id == ricetta_id).first()
    if pa is None:
        pa = ProfiloAcqua(ricetta_id=ricetta_id)
        db.add(pa)

    pa.nome = nome
    pa.ca = ca
    pa.mg = mg
    pa.na = na
    pa.cl = cl
    pa.so4 = so4
    try:
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(f"/ricette/{ricetta_id}?msg=Errore+salvataggio+profilo+acqua#profilo-acqua", status_code=303)

    return RedirectResponse(f"/ricette/{ricetta_id}#profilo-acqua", status_code=303)


@router.post("/ricette/{ricetta_id}/profilo-mash")
@router.post("/ricette/{ricetta_id}/profilo-mash-save")
async def salva_profilo_mash_full(
    ricetta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    is_json = False
    data = {}
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            data = await request.json()
            is_json = True
        except Exception:
            data = {}
    else:
        form = await request.form()
        data = dict(form)

    # 1. Controllo se richiesta eliminazione
    if data.get("action") == "elimina" or data.get("elimina") in ("1", "true", True):
        db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).delete(synchronize_session=False)
        db.commit()
        if is_json or "application/json" in request.headers.get("accept", ""):
            return JSONResponse({"status": "deleted"})
        return RedirectResponse(f"/ricette/{ricetta_id}?msg=Profilo+ammostamento+rimosso#profilo-mash", status_code=303)

    # 2. Controllo se selezionato un preset
    template_preset = data.get("template_preset") or data.get("preset") or data.get("tipo_mash")
    nome_profilo = (data.get("nome_profilo") or "").strip()
    steps = []

    if template_preset and get_template_steps(template_preset):
        steps = get_template_steps(template_preset)
        if not nome_profilo:
            nome_profilo = MASH_TEMPLATES_ALIASES.get(template_preset, template_preset)
    elif is_json and "steps" in data and isinstance(data["steps"], list):
        for i, s in enumerate(data["steps"]):
            if isinstance(s, dict):
                s_name = str(s.get("nome") or f"Step {i+1}").strip()
                s_temp = _parse_temp(s.get("temp_gradi") or s.get("temp") or 67.0)
                s_dur = _parse_durata(s.get("durata_min") or s.get("durata") or 60)
                s_tipo = str(s.get("tipo") or "Temperature").strip()
                steps.append({"nome": s_name, "temp_gradi": s_temp, "durata_min": s_dur, "tipo": s_tipo})
    else:
        form = await request.form() if not is_json else {}
        nomi = form.getlist("step_nome") if hasattr(form, "getlist") else []
        tempi = form.getlist("step_temp") if hasattr(form, "getlist") else []
        durate = form.getlist("step_durata") if hasattr(form, "getlist") else []
        tipi = form.getlist("step_tipo") if hasattr(form, "getlist") else []

        for i, (n, t, d) in enumerate(zip(nomi, tempi, durate)):
            s_name = str(n).strip() if (n and str(n).strip()) else f"Step {i+1}"
            s_temp = _parse_temp(t)
            s_dur = _parse_durata(d)
            s_tipo = (tipi[i] if i < len(tipi) and tipi[i] else "Temperature").strip()
            steps.append({
                "nome": s_name,
                "temp_gradi": s_temp,
                "durata_min": s_dur,
                "tipo": s_tipo,
            })

    if not nome_profilo:
        nome_profilo = "Singolo infuso"

    pm = (
        db.query(ProfiloAmmostamento)
        .filter(ProfiloAmmostamento.ricetta_id == ricetta_id)
        .first()
    )
    if pm is None:
        pm = ProfiloAmmostamento(ricetta_id=ricetta_id)
        db.add(pm)

    pm.nome = nome_profilo
    pm.steps_json = json.dumps(steps, ensure_ascii=False)
    try:
        db.commit()
    except Exception:
        db.rollback()
        if is_json:
            return JSONResponse({"status": "error", "message": "Errore salvataggio database"}, status_code=500)
        return RedirectResponse(f"/ricette/{ricetta_id}?msg=Errore+salvataggio+profilo+mash#profilo-mash", status_code=303)

    if is_json or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"status": "ok", "nome": pm.nome, "steps": steps, "count": len(steps)})

    return RedirectResponse(f"/ricette/{ricetta_id}?msg=Profilo+ammostamento+salvato#profilo-mash", status_code=303)


@router.post("/ricette/{ricetta_id}/profilo-mash-elimina")
def elimina_profilo_mash(
    ricetta_id: int,
    db: Session = Depends(get_db),
):
    db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).delete(synchronize_session=False)
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}?msg=Profilo+ammostamento+rimosso#profilo-mash", status_code=303)


@router.post("/ricette/{ricetta_id}/avvia-cotta")
def avvia_cotta_da_ricetta(
    ricetta_id: int,
    nome: str = Form(...),
    codice: str = Form(""),
    data_brew: str = Form(""),
    fermentatore: str = Form(""),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    c_codice = codice.strip().upper() if codice and codice.strip() else genera_prossimo_codice_cotta(date.today().year, db)
    cotta = Cotta(
        nome=nome,
        codice=c_codice,
        ricetta_id=ricetta_id,
        data_brew=data_brew or None,
        fermentatore=fermentatore or None,
        stato="pianificata",
    )
    db.add(cotta)
    db.flush()

    db.add(
        LogCotta(
            cotta_id=cotta.id,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            fase="pianificata",
            tipo="evento",
            descrizione=f"Cotta avviata dalla ricetta: {ricetta.nome}",
        )
    )
    db.commit()

    return RedirectResponse(f"/cotte/{cotta.id}", status_code=303)


@router.get("/ricette/{ricetta_id}/stats-json")
def stats_json(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return {"error": "not found"}

    ingredienti = (
        db.query(IngredienteRicetta)
        .filter(IngredienteRicetta.ricetta_id == ricetta_id)
        .all()
    )
    stats = calcola_stats(ricetta, ingredienti)
    stile_corrente = (
        db.query(Stile).filter(Stile.id == ricetta.stile_id).first()
        if ricetta.stile_id
        else None
    )
    cf = confronta_stile(stats, stile_corrente)
    costo = calcola_costo(ingredienti)

    return {
        "stats": stats,
        "confronto_stile": cf,
        "costo": costo,
        "srm_hex": srm_to_hex(stats["srm"]),
    }


@router.post("/ricette/{ricetta_id}/assegna-stile")
def assegna_stile(
    ricetta_id: int, stile_id: int = Form(...), db: Session = Depends(get_db)
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    ricetta.stile_id = stile_id if stile_id != 0 else None
    db.commit()

    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.get("/ricette/{ricetta_id}/catalogo", response_class=HTMLResponse)
def catalogo_per_ricetta(
    ricetta_id: int,
    request: Request,
    categoria: str = None,
    db: Session = Depends(get_db),
):
    from ..models import CatalogoIngrediente

    try:
        query = db.query(CatalogoIngrediente)
        if categoria:
            query = query.filter(CatalogoIngrediente.categoria == categoria)
        items = query.all()
        all_items = db.query(CatalogoIngrediente).all()
    except Exception:
        db.rollback()
        items = []
        all_items = []

    per_cat = {}
    for i in all_items:
        cat = getattr(i, "categoria", None) or "misc"
        per_cat[cat] = per_cat.get(cat, 0) + 1
    items_sorted = sorted(items, key=lambda i: (getattr(i, "nome", "") or "").lower())

    return templates.TemplateResponse(
        request,
        "catalogo_ingredienti.html",
        {
            "request": request,
            "session": request.session,
            "items": items_sorted,
            "totale": len(all_items),
            "per_cat": per_cat,
            "msg": None,
            "ricetta_id": ricetta_id,
            "categoria_attiva": categoria,
        },
    )


@router.get("/ricette/{ricetta_id}/modifica", response_class=HTMLResponse)
def form_modifica_ricetta(
    ricetta_id: int,
    request: Request,
    saved: bool = False,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    stili = db.query(Stile).order_by(Stile.linea_guida, Stile.nome).all()
    stile_corrente = (
        db.query(Stile).filter(Stile.id == ricetta.stile_id).first()
        if ricetta.stile_id
        else None
    )

    profilo_mash = db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).first()
    return templates.TemplateResponse(
        request,
        "modifica_ricetta.html",
        {
            "request": request,
            "ricetta": ricetta,
            "stili": stili,
            "stile_corrente": stile_corrente,
            "saved": saved,
            "profilo_mash": profilo_mash,
            "mash_templates": MASH_TEMPLATES,
        },
    )


@router.post("/ricette/{ricetta_id}/modifica")
def salva_modifica_ricetta(
    ricetta_id: int,
    nome: str = Form(...),
    codice: str = Form(""),
    tipo: str = Form(...),
    volume_target_litri: float = Form(...),
    efficienza: float = Form(...),
    versione: int = Form(...),
    stile_id: int = Form(0),
    note: str = Form(""),
    tipo_mash: str = Form(""),
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    ricetta.nome = nome
    if codice and codice.strip():
        ricetta.codice = codice.strip().upper()
    elif not ricetta.codice:
        ricetta.codice = genera_prossimo_codice_ricetta(db)
    ricetta.tipo = tipo
    ricetta.volume_target_litri = volume_target_litri
    ricetta.efficienza = efficienza
    ricetta.versione = versione
    ricetta.stile_id = stile_id if stile_id != 0 else None
    ricetta.note = note or None

    if tipo_mash:
        if tipo_mash == "none":
            db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).delete(synchronize_session=False)
        else:
            t_steps = get_template_steps(tipo_mash)
            if t_steps:
                nome_clean = MASH_TEMPLATES_ALIASES.get(tipo_mash, tipo_mash)
                pm = db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).first()
                if not pm:
                    pm = ProfiloAmmostamento(ricetta_id=ricetta_id)
                    db.add(pm)
                pm.nome = nome_clean
                pm.steps_json = json.dumps(t_steps, ensure_ascii=False)

    try:
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse(f"/ricette/{ricetta_id}/modifica?error=Errore+salvataggio", status_code=303)

    return RedirectResponse(
        f"/ricette/{ricetta_id}/modifica?saved=true", status_code=303
    )


@router.get("/ricette/{ricetta_id}/elimina")
def elimina_ricetta(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if ricetta:
        cotte_collegate = db.query(Cotta).filter(Cotta.ricetta_id == ricetta_id).count()
        if cotte_collegate > 0:
            return RedirectResponse(
                f"/ricette/html?msg=Impossibile+eliminare:+la+ricetta+è+collegata+a+{cotte_collegate}+cotte+storiche",
                status_code=303,
            )
        try:
            from ..models import Vendita
            db.query(Vendita).filter(Vendita.ricetta_id == ricetta_id).update({"ricetta_id": None}, synchronize_session=False)
            db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).delete(synchronize_session=False)
            db.query(ProfiloAcqua).filter(ProfiloAcqua.ricetta_id == ricetta_id).delete(synchronize_session=False)
            db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).delete(synchronize_session=False)
            db.delete(ricetta)
            db.commit()
        except Exception:
            db.rollback()
            return RedirectResponse(
                "/ricette/html?msg=Errore+durante+l+eliminazione+della+ricetta",
                status_code=303,
            )
    return RedirectResponse("/ricette/html?msg=Ricetta+eliminata", status_code=303)


@router.get("/ricette/{ricetta_id}/beerxml")
def esporta_beerxml(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return Response("Ricetta non trovata", status_code=404)

    ingredienti = (
        db.query(IngredienteRicetta)
        .filter(IngredienteRicetta.ricetta_id == ricetta_id)
        .all()
    )

    # Calcola stats per OG/FG/IBU/colore
    stats = calcola_stats(ricetta, ingredienti)

    root = Element("RECIPES")
    r_el = SubElement(root, "RECIPE")
    SubElement(r_el, "NAME").text = ricetta.nome
    SubElement(r_el, "VERSION").text = "1"
    SubElement(r_el, "TYPE").text = ricetta.tipo or "All Grain"
    SubElement(r_el, "BATCH_SIZE").text = str(ricetta.volume_target_litri or 20.0)
    SubElement(r_el, "BOIL_SIZE").text = str(round((ricetta.volume_target_litri or 20.0) * 1.20, 1))
    SubElement(r_el, "BOIL_TIME").text = "60"
    SubElement(r_el, "EFFICIENCY").text = str(ricetta.efficienza or 75.0)
    if stats.get("og"):
        SubElement(r_el, "OG").text = str(stats["og"])
    if stats.get("fg"):
        SubElement(r_el, "FG").text = str(stats["fg"])
    if stats.get("ibu"):
        SubElement(r_el, "IBU").text = str(stats["ibu"])
    if stats.get("srm"):
        SubElement(r_el, "COLOR").text = str(stats["srm"])
    if stats.get("abv"):
        SubElement(r_el, "ABV").text = str(stats["abv"])
    if ricetta.note:
        SubElement(r_el, "NOTES").text = ricetta.note

    # STYLE
    if ricetta.stile:
        st_el = SubElement(r_el, "STYLE")
        SubElement(st_el, "NAME").text = ricetta.stile.nome
        SubElement(st_el, "VERSION").text = "1"
        SubElement(st_el, "CATEGORY").text = ricetta.stile.nome
        SubElement(st_el, "CATEGORY_NUMBER").text = "0"
        SubElement(st_el, "STYLE_LETTER").text = "A"
        SubElement(st_el, "STYLE_GUIDE").text = "BJCP"
        SubElement(st_el, "TYPE").text = "Ale"
        if ricetta.stile.og_min: SubElement(st_el, "OG_MIN").text = str(ricetta.stile.og_min)
        if ricetta.stile.og_max: SubElement(st_el, "OG_MAX").text = str(ricetta.stile.og_max)
        if ricetta.stile.fg_min: SubElement(st_el, "FG_MIN").text = str(ricetta.stile.fg_min)
        if ricetta.stile.fg_max: SubElement(st_el, "FG_MAX").text = str(ricetta.stile.fg_max)
        if ricetta.stile.ibu_min: SubElement(st_el, "IBU_MIN").text = str(ricetta.stile.ibu_min)
        if ricetta.stile.ibu_max: SubElement(st_el, "IBU_MAX").text = str(ricetta.stile.ibu_max)

    fermentables = SubElement(r_el, "FERMENTABLES")
    hops = SubElement(r_el, "HOPS")
    yeasts = SubElement(r_el, "YEASTS")
    miscs = SubElement(r_el, "MISCS")

    for i in ingredienti:
        if i.categoria == "grain":
            fe = SubElement(fermentables, "FERMENTABLE")
            SubElement(fe, "NAME").text = i.nome
            SubElement(fe, "VERSION").text = "1"
            SubElement(fe, "AMOUNT").text = str(i.quantita)
            SubElement(fe, "TYPE").text = "Grain"
            if i.yield_percent:
                SubElement(fe, "YIELD").text = str(i.yield_percent)
            else:
                SubElement(fe, "YIELD").text = "75.0"
            if i.color_srm:
                SubElement(fe, "COLOR").text = str(i.color_srm)
            else:
                SubElement(fe, "COLOR").text = "2"

        elif i.categoria == "hop":
            he = SubElement(hops, "HOP")
            SubElement(he, "NAME").text = i.nome
            SubElement(he, "VERSION").text = "1"
            SubElement(he, "AMOUNT").text = str(i.quantita)
            if i.alpha_acid:
                SubElement(he, "ALPHA").text = str(i.alpha_acid)
            else:
                SubElement(he, "ALPHA").text = "5.0"
            if i.time_min is not None:
                SubElement(he, "TIME").text = str(i.time_min)
                if i.time_min == 0:
                    SubElement(he, "USE").text = "Dry Hop"
                else:
                    SubElement(he, "USE").text = "Boil"
            else:
                SubElement(he, "USE").text = "Boil"
                SubElement(he, "TIME").text = "60"
            if i.hop_form:
                SubElement(he, "FORM").text = i.hop_form.capitalize()

        elif i.categoria == "yeast":
            ye = SubElement(yeasts, "YEAST")
            SubElement(ye, "NAME").text = i.nome
            SubElement(ye, "VERSION").text = "1"
            SubElement(ye, "AMOUNT").text = str(i.quantita or 1)
            SubElement(ye, "TYPE").text = "Ale"
            SubElement(ye, "FORM").text = i.yeast_form.capitalize() if i.yeast_form else "Dry"
            if i.attenuation:
                SubElement(ye, "ATTENUATION").text = str(i.attenuation)

        elif i.categoria in ("misc", "other", "spice", "water"):
            me = SubElement(miscs, "MISC")
            SubElement(me, "NAME").text = i.nome
            SubElement(me, "VERSION").text = "1"
            SubElement(me, "AMOUNT").text = str(i.quantita)
            SubElement(me, "TYPE").text = "Other"
            SubElement(me, "USE").text = "Boil"
            if i.time_min is not None:
                SubElement(me, "TIME").text = str(i.time_min)

    # MASH profile
    if ricetta.profilo_mash:
        mash_el = SubElement(r_el, "MASH")
        SubElement(mash_el, "NAME").text = ricetta.profilo_mash.nome or "Singolo infuso"
        SubElement(mash_el, "VERSION").text = "1"
        steps_el = SubElement(mash_el, "MASH_STEPS")
        mash_steps = []
        if ricetta.profilo_mash.steps_json:
            try:
                parsed_steps = json.loads(ricetta.profilo_mash.steps_json)
                mash_steps = parsed_steps if isinstance(parsed_steps, list) else []
            except Exception:
                mash_steps = []
        for step in mash_steps:
            if isinstance(step, dict):
                s_el = SubElement(steps_el, "MASH_STEP")
                SubElement(s_el, "NAME").text = str(step.get("nome") or "Saccarificazione")
                SubElement(s_el, "VERSION").text = "1"
                SubElement(s_el, "TYPE").text = "Infusion"
                SubElement(s_el, "STEP_TEMP").text = str(step.get("temp_gradi") or step.get("temp") or 67)
                SubElement(s_el, "STEP_TIME").text = str(step.get("durata_min") or step.get("durata") or 60)

    xml_str = minidom.parseString(tostring(root, encoding="unicode")).toprettyxml(
        indent="  "
    )
    return Response(
        content=xml_str,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{ricetta.nome}.xml"'},
    )


@router.post("/ricette/{ricetta_id}/assegna-impianto")
def assegna_impianto(
    ricetta_id: int,
    profilo_birrificio_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    ricetta.profilo_birrificio_id = profilo_birrificio_id if profilo_birrificio_id and profilo_birrificio_id > 0 else None
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.post("/ricette/{ricetta_id}/scala")
async def scala_ricetta(
    ricetta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    form = await request.form()
    raw_vol = form.get("volume_target_litri") or form.get("nuovo_volume") or ricetta.volume_target_litri or 20.0
    raw_eff = form.get("efficienza") or form.get("nuova_efficienza") or ricetta.efficienza or 75.0
    raw_og = form.get("target_og") or form.get("nuova_og")
    raw_ibu = form.get("target_ibu") or form.get("nuovi_ibu")
    clona = form.get("clona") == "1"

    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    old_stats = calcola_stats(ricetta, ingredienti)

    old_vol = float(ricetta.volume_target_litri or 20.0)
    old_eff = float(ricetta.efficienza or 75.0)
    new_vol = max(1.0, float(str(raw_vol).replace(",", ".")))
    new_eff = float(str(raw_eff).replace(",", ".")) if raw_eff else old_eff

    grain_factor = (new_vol / max(1.0, old_vol)) * (old_eff / max(1.0, new_eff))
    if raw_og and str(raw_og).strip():
        try:
            f_og = float(str(raw_og).replace(",", "."))
            if f_og > 1.0 and old_stats.get("og", 1.0) > 1.0:
                target_pts = (f_og - 1.0) * 1000.0
                current_pts = max(1.0, (old_stats["og"] - 1.0) * 1000.0)
                grain_factor *= (target_pts / current_pts)
        except ValueError:
            pass

    target_ibu = old_stats.get("ibu", 0.0)
    if raw_ibu and str(raw_ibu).strip():
        try:
            target_ibu = float(str(raw_ibu).replace(",", "."))
        except ValueError:
            pass
    current_ibu = max(0.1, old_stats.get("ibu", 0.0))
    hop_factor = (new_vol / max(1.0, old_vol)) * (target_ibu / current_ibu if current_ibu > 0 and target_ibu > 0 else 1.0)

    if clona:
        nuovo_cod = genera_prossimo_codice_ricetta(db)
        nuova_ric = Ricetta(
            codice=nuovo_cod,
            nome=f"{ricetta.nome} ({int(new_vol) if new_vol.is_integer() else new_vol}L)",
            tipo=ricetta.tipo,
            volume_target_litri=round(new_vol, 1),
            efficienza=round(new_eff, 1),
            versione=(ricetta.versione or 1) + 1,
            note=ricetta.note,
            stile_id=ricetta.stile_id,
            profilo_birrificio_id=ricetta.profilo_birrificio_id,
            profilo_fermentazione_json=ricetta.profilo_fermentazione_json,
        )
        db.add(nuova_ric)
        db.flush()
        for i in ingredienti:
            q_new = float(i.quantita or 0)
            if i.categoria == "grain":
                q_new = round(q_new * grain_factor, 3)
            elif i.categoria == "hop":
                q_new = round(q_new * hop_factor, 1)
            db.add(IngredienteRicetta(
                ricetta_id=nuova_ric.id,
                codice_ingrediente=i.codice_ingrediente,
                nome=i.nome,
                categoria=i.categoria,
                quantita=q_new,
                unita=i.unita,
                note=i.note,
                time_min=i.time_min,
                prezzo_unitario=i.prezzo_unitario,
                fermentable_type=i.fermentable_type,
                yield_percent=i.yield_percent,
                color_srm=i.color_srm,
                alpha_acid=i.alpha_acid,
                hop_use=i.hop_use,
                hop_form=i.hop_form,
                attenuation=i.attenuation,
                yeast_type=i.yeast_type,
                yeast_form=i.yeast_form,
                misc_type=i.misc_type,
                misc_use=i.misc_use,
            ))
        db.commit()
        return RedirectResponse(f"/ricette/{nuova_ric.id}", status_code=303)

    for i in ingredienti:
        if i.categoria == "grain" and i.quantita:
            i.quantita = round(float(i.quantita) * grain_factor, 3)
        elif i.categoria == "hop" and i.quantita:
            i.quantita = round(float(i.quantita) * hop_factor, 1)

    ricetta.volume_target_litri = round(new_vol, 1)
    ricetta.efficienza = round(new_eff, 1)
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.post("/ricette/{ricetta_id}/adatta-aa")
def adatta_aa_luppoli(ricetta_id: int, db: Session = Depends(get_db)):
    """Adatta automaticamente i grammi dei luppoli in ricetta in base agli Alfa Acidi dei lotti presenti in magazzino, mantenendo costanti gli IBU."""
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    inv_items = db.query(InventarioItem).all()
    fatt = _calcola_fattibilita_ricetta(ingredienti, inv_items)
    det = fatt.get("dettaglio", {})
    for ing in ingredienti:
        info = det.get(ing.id)
        if ing.categoria == "hop" and info and info.get("qty_aa_adj") and info.get("aa_lotto"):
            ing.quantita = info["qty_aa_adj"]
            ing.alpha_acid = info["aa_lotto"]
            if info.get("lotto"):
                ing.numero_lotto = info["lotto"]
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.post("/ricette/{ricetta_id}/mancanti-lista-spesa")
def aggiungi_mancanti_lista_spesa(ricetta_id: int, request: Request, db: Session = Depends(get_db)):
    """Invia in 1 click tutti gli ingredienti mancanti per questa ricetta alla Lista della Spesa."""
    from ..models import ListaAcquisti
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    inv_items = db.query(InventarioItem).all()
    fatt = _calcola_fattibilita_ricetta(ingredienti, inv_items)
    uid = request.session.get("user_id")
    for m in fatt.get("mancanti", []):
        db.add(ListaAcquisti(
            nome=m["nome"],
            categoria="ingrediente",
            quantita=m["manca"],
            unita=m["unita"],
            priorita=1,
            note=f"Mancante per ricetta {ricetta.codice or ''} {ricetta.nome}".strip(),
            completato=False,
            user_id=uid if uid else None,
        ))
    db.commit()
    return RedirectResponse("/lista-acquisti", status_code=303)


@router.post("/ricette/{ricetta_id}/profilo-fermentazione")
async def salva_profilo_fermentazione(
    ricetta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    form = await request.form()
    steps_json = form.get("steps_json")
    if steps_json:
        try:
            parsed = json.loads(steps_json)
            ricetta.profilo_fermentazione_json = json.dumps(parsed)
        except Exception:
            ricetta.profilo_fermentazione_json = steps_json
    else:
        nomi = form.getlist("step_nome")
        temps = form.getlist("step_temp")
        giorni = form.getlist("step_giorni")
        tipi = form.getlist("step_tipo")
        steps = []
        for idx, n in enumerate(nomi):
            if not n.strip():
                continue
            t_val = _parse_temp(temps[idx] if idx < len(temps) else 19.0, 19.0)
            g_val = _parse_durata(giorni[idx] if idx < len(giorni) else 7, 7)
            tp_val = tipi[idx] if idx < len(tipi) else "primaria"
            steps.append({"nome": n.strip(), "temp": t_val, "giorni": g_val, "tipo": tp_val})
        ricetta.profilo_fermentazione_json = json.dumps(steps, ensure_ascii=False)
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}#card-fermentazione-priming", status_code=303)


@router.get("/ricette/{ricetta_id}/stampa", response_class=HTMLResponse)
def scheda_cotta_stampa(
    ricetta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    grani = [i for i in ingredienti if i.categoria == "grain"]
    luppoli = sorted([i for i in ingredienti if i.categoria == "hop"], key=lambda x: (x.time_min or 0), reverse=True)
    lieviti = [i for i in ingredienti if i.categoria == "yeast"]
    altri = [i for i in ingredienti if i.categoria not in ("grain", "hop", "yeast")]

    stats = calcola_stats(ricetta, ingredienti)
    stile = db.query(Stile).filter(Stile.id == ricetta.stile_id).first() if ricetta.stile_id else None
    cf = confronta_stile(stats, stile)
    profilo_mash = db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).first()
    profilo_acqua = db.query(ProfiloAcqua).filter(ProfiloAcqua.ricetta_id == ricetta_id).first()

    mash_steps = []
    if profilo_mash and profilo_mash.steps_json:
        try:
            mash_steps = json.loads(profilo_mash.steps_json)
        except Exception:
            mash_steps = []

    ferm_steps = []
    if ricetta.profilo_fermentazione_json:
        try:
            ferm_steps = json.loads(ricetta.profilo_fermentazione_json)
        except Exception:
            ferm_steps = []

    return templates.TemplateResponse(
        request,
        "brew_sheet.html",
        {
            "request": request,
            "ricetta": ricetta,
            "grani": grani,
            "luppoli": luppoli,
            "lieviti": lieviti,
            "altri": altri,
            "stats": stats,
            "stile": stile,
            "confronto_stile": cf,
            "mash_steps": mash_steps,
            "profilo_acqua": profilo_acqua,
            "ferm_steps": ferm_steps,
            "oggi": date.today().strftime("%d/%m/%Y"),
        },
    )

