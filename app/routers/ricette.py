import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
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
)
from ..stats import (
    calcola_stats,
    confronta_stile,
    calcola_percentuali,
    calcola_costo,
    srm_to_hex,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["srm_to_hex"] = srm_to_hex


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/ricette/html", response_class=HTMLResponse)
def lista_ricette(request: Request, db: Session = Depends(get_db)):
    ricette = db.query(Ricetta).all()
    stili = db.query(Stile).order_by(Stile.linea_guida, Stile.nome).all()
    profili_preset = db.query(ProfiloAcquaPreset).order_by(ProfiloAcquaPreset.nome).all()

    counts_q = (
        db.query(Cotta.ricetta_id, func.count(Cotta.id))
        .group_by(Cotta.ricetta_id)
        .all()
    )
    cotte_count = {rid: cnt for rid, cnt in counts_q if rid is not None}

    return templates.TemplateResponse(
        "ricette.html",
        {
            "request": request,
            "ricette": ricette,
            "stili": stili,
            "profili_preset": profili_preset,
            "cotte_count": cotte_count,
        },
    )


@router.post("/ricette/html")
def crea_ricetta(
    nome: str = Form(...),
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
    r = Ricetta(
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

    MASH_TEMPLATES = {
        "Singolo Infuso": [{"nome": "Saccarificazione", "temp_gradi": 67, "durata_min": 60}],
        "BIAB": [
            {"nome": "Saccarificazione", "temp_gradi": 67, "durata_min": 60},
            {"nome": "Mash Out", "temp_gradi": 77, "durata_min": 10},
        ],
        "Step Mash": [
            {"nome": "Protein Rest", "temp_gradi": 52, "durata_min": 15},
            {"nome": "Saccarificazione", "temp_gradi": 67, "durata_min": 45},
            {"nome": "Mash Out", "temp_gradi": 77, "durata_min": 10},
        ],
        "Decozione": [
            {"nome": "Ammostamento 1", "temp_gradi": 62, "durata_min": 30},
            {"nome": "Decozione", "temp_gradi": 72, "durata_min": 30},
        ],
        "No-Sparge": [{"nome": "Saccarificazione", "temp_gradi": 67, "durata_min": 75}],
    }
    if tipo_mash and tipo_mash in MASH_TEMPLATES:
        pm = ProfiloAmmostamento(
            ricetta_id=r.id,
            nome=tipo_mash,
            steps_json=_json.dumps(MASH_TEMPLATES[tipo_mash], ensure_ascii=False),
        )
        db.add(pm)

    try:
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/ricette/html?msg=Errore+creazione+ricetta", status_code=303)
    return RedirectResponse(f"/ricette/{r.id}", status_code=303)


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

    profili_preset_acqua = db.query(ProfiloAcquaPreset).order_by(ProfiloAcquaPreset.nome).all()
    catalogo_items = db.query(CatalogoIngrediente).order_by(CatalogoIngrediente.categoria, CatalogoIngrediente.nome).all()
    inventario_items = db.query(InventarioItem).order_by(InventarioItem.categoria, InventarioItem.nome).all()

    return templates.TemplateResponse(
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
            "profili_preset_acqua": profili_preset_acqua,
            "catalogo_items": catalogo_items,
            "inventario_items": inventario_items,
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
        ing = IngredienteRicetta(
            ricetta_id=ricetta_id,
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
def salva_profilo_mash_placeholder(
    ricetta_id: int,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    return RedirectResponse(f"/ricette/{ricetta_id}#profilo-mash", status_code=303)


@router.post("/ricette/{ricetta_id}/profilo-mash-save")
async def salva_profilo_mash_full(
    ricetta_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    form = await request.form()
    nome_profilo = form.get("nome_profilo", "Singolo infuso")
    nomi = form.getlist("step_nome")
    tempi = form.getlist("step_temp")
    durate = form.getlist("step_durata")

    steps = []
    for n, t, d in zip(nomi, tempi, durate):
        if n.strip():
            try:
                steps.append(
                    {
                        "nome": n.strip(),
                        "temp_gradi": float(t) if t else 0.0,
                        "durata_min": int(d) if d else 0,
                    }
                )
            except Exception:
                pass

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
        return RedirectResponse(f"/ricette/{ricetta_id}?msg=Errore+salvataggio+profilo+mash#profilo-mash", status_code=303)

    return RedirectResponse(f"/ricette/{ricetta_id}#profilo-mash", status_code=303)


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

    cotta = Cotta(
        nome=nome,
        codice=codice or None,
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

    return templates.TemplateResponse(
        "modifica_ricetta.html",
        {
            "request": request,
            "ricetta": ricetta,
            "stili": stili,
            "stile_corrente": stile_corrente,
            "saved": saved,
        },
    )


@router.post("/ricette/{ricetta_id}/modifica")
def salva_modifica_ricetta(
    ricetta_id: int,
    nome: str = Form(...),
    tipo: str = Form(...),
    volume_target_litri: float = Form(...),
    efficienza: float = Form(...),
    versione: int = Form(...),
    stile_id: int = Form(0),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    ricetta.nome = nome
    ricetta.tipo = tipo
    ricetta.volume_target_litri = volume_target_litri
    ricetta.efficienza = efficienza
    ricetta.versione = versione
    ricetta.stile_id = stile_id if stile_id != 0 else None
    ricetta.note = note or None
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
            from ..models import CondivisioneRicetta
            db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).delete(synchronize_session=False)
            db.query(ProfiloAcqua).filter(ProfiloAcqua.ricetta_id == ricetta_id).delete(synchronize_session=False)
            db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).delete(synchronize_session=False)
            db.query(CondivisioneRicetta).filter(CondivisioneRicetta.ricetta_id == ricetta_id).delete(synchronize_session=False)
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
