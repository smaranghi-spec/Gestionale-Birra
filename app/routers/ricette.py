import json
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from ..db import SessionLocal
from ..models import Ricetta, IngredienteRicetta, Stile, Cotta, LogCotta, ProfiloAcqua, ProfiloAmmostamento
from ..stats import calcola_stats, confronta_stile, calcola_percentuali, calcola_costo, srm_to_hex

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/ricette/html", response_class=HTMLResponse)
def lista_ricette(request: Request, db: Session = Depends(get_db)):
    ricette = db.query(Ricetta).all()
    from sqlalchemy import func
    counts_q = db.query(Cotta.ricetta_id, func.count(Cotta.id)).group_by(Cotta.ricetta_id).all()
    cotte_count = {rid: cnt for rid, cnt in counts_q}
    stili = db.query(Stile).order_by(Stile.linea_guida, Stile.nome).all()
    return templates.TemplateResponse(request, "ricette.html", {
        "ricette": ricette,
        "cotte_count": cotte_count,
        "stili": stili,
    })


@router.post("/ricette/html")
def crea_ricetta(
    nome: str = Form(...),
    tipo: str = Form(...),
    volume_target_litri: float = Form(...),
    efficienza: float = Form(...),
    versione: int = Form(...),
    stile_id: int = Form(0),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
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
    db.commit()
    return RedirectResponse("/ricette/html", status_code=303)


@router.get("/ricette/{ricetta_id}", response_class=HTMLResponse)
def dettaglio_ricetta(ricetta_id: int, request: Request, db: Session = Depends(get_db)):
    from datetime import date
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return HTMLResponse("Ricetta non trovata", status_code=404)

    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    stili = db.query(Stile).all()
    stats = calcola_stats(ricetta, ingredienti)
    stile_corrente = db.query(Stile).filter(Stile.id == ricetta.stile_id).first() if ricetta.stile_id else None
    cf = confronta_stile(stats, stile_corrente)
    percentuali = calcola_percentuali(ingredienti)
    costo = calcola_costo(ingredienti)
    srm_hex = srm_to_hex(stats["srm"])

    cotte = db.query(Cotta).filter(Cotta.ricetta_id == ricetta_id).order_by(Cotta.id.desc()).all()
    n_cotte = len(cotte)

    profilo_acqua = db.query(ProfiloAcqua).filter(ProfiloAcqua.ricetta_id == ricetta_id).first()
    profilo_mash = db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).first()

    mash_steps = []
    if profilo_mash and profilo_mash.steps_json:
        try:
            mash_steps = json.loads(profilo_mash.steps_json)
        except Exception:
            mash_steps = []

    return templates.TemplateResponse(request, "dettaglio_ricetta.html", {
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
    })


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
    pa.hco3 = hco3
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}#profilo-acqua", status_code=303)


@router.post("/ricette/{ricetta_id}/profilo-mash")
def salva_profilo_mash(
    ricetta_id: int,
    request: Request,
    nome_profilo: str = Form("Singolo infuso"),
    db: Session = Depends(get_db),
):
    import asyncio
    form_data = asyncio.get_event_loop().run_until_complete(request.form()) if False else None

    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    from starlette.datastructures import FormData
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
                steps.append({
                    "nome": n.strip(),
                    "temp_gradi": float(t) if t else 0.0,
                    "durata_min": int(d) if d else 0,
                })
            except Exception:
                pass

    pm = db.query(ProfiloAmmostamento).filter(ProfiloAmmostamento.ricetta_id == ricetta_id).first()
    if pm is None:
        pm = ProfiloAmmostamento(ricetta_id=ricetta_id)
        db.add(pm)
    pm.nome = nome_profilo
    pm.steps_json = json.dumps(steps, ensure_ascii=False)
    db.commit()
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
    db.add(LogCotta(
        cotta_id=cotta.id,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        fase="pianificata",
        tipo="evento",
        descrizione=f"Cotta avviata dalla ricetta: {ricetta.nome}",
    ))
    db.commit()
    return RedirectResponse(f"/cotte/{cotta.id}", status_code=303)


@router.get("/ricette/{ricetta_id}/stats-json")
def stats_json(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return {"error": "not found"}
    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    stats = calcola_stats(ricetta, ingredienti)
    stile_corrente = db.query(Stile).filter(Stile.id == ricetta.stile_id).first() if ricetta.stile_id else None
    cf = confronta_stile(stats, stile_corrente)
    costo = calcola_costo(ingredienti)
    return {"stats": stats, "confronto_stile": cf, "costo": costo, "srm_hex": srm_to_hex(stats["srm"])}


@router.post("/ricette/{ricetta_id}/assegna-stile")
def assegna_stile(ricetta_id: int, stile_id: int = Form(...), db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    ricetta.stile_id = stile_id if stile_id != 0 else None
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.get("/ricette/{ricetta_id}/catalogo", response_class=HTMLResponse)
def catalogo_per_ricetta(ricetta_id: int, request: Request, categoria: str = None, db: Session = Depends(get_db)):
    from ..models import CatalogoIngrediente
    query = db.query(CatalogoIngrediente)
    if categoria:
        query = query.filter(CatalogoIngrediente.categoria == categoria)
    items = query.all()
    return templates.TemplateResponse(request, "catalogo_ingredienti.html", {
        "items": items,
        "ricetta_id": ricetta_id,
        "categoria_attiva": categoria,
    })


@router.get("/ricette/{ricetta_id}/modifica", response_class=HTMLResponse)
def form_modifica_ricetta(ricetta_id: int, request: Request, saved: bool = False, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)
    stili = db.query(Stile).order_by(Stile.linea_guida, Stile.nome).all()
    stile_corrente = db.query(Stile).filter(Stile.id == ricetta.stile_id).first() if ricetta.stile_id else None
    return templates.TemplateResponse(request, "modifica_ricetta.html", {
        "ricetta": ricetta,
        "stili": stili,
        "stile_corrente": stile_corrente,
        "saved": saved,
    })


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
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}/modifica?saved=true", status_code=303)


@router.get("/ricette/{ricetta_id}/elimina")
def elimina_ricetta(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if ricetta:
        db.delete(ricetta)
        db.commit()
    return RedirectResponse("/ricette/html", status_code=303)


@router.get("/ricette/{ricetta_id}/beerxml")
def esporta_beerxml(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return Response("Ricetta non trovata", status_code=404)
    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()

    root = Element("RECIPES")
    r_el = SubElement(root, "RECIPE")
    SubElement(r_el, "NAME").text = ricetta.nome
    SubElement(r_el, "VERSION").text = str(ricetta.versione)
    SubElement(r_el, "TYPE").text = ricetta.tipo
    SubElement(r_el, "BATCH_SIZE").text = str(ricetta.volume_target_litri)
    SubElement(r_el, "EFFICIENCY").text = str(ricetta.efficienza)
    if ricetta.note:
        SubElement(r_el, "NOTES").text = ricetta.note

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
            if i.yield_percent:
                SubElement(fe, "YIELD").text = str(i.yield_percent)
            if i.color_srm:
                SubElement(fe, "COLOR").text = str(i.color_srm)
        elif i.categoria == "hop":
            he = SubElement(hops, "HOP")
            SubElement(he, "NAME").text = i.nome
            SubElement(he, "VERSION").text = "1"
            SubElement(he, "AMOUNT").text = str(i.quantita)
            if i.alpha_acid:
                SubElement(he, "ALPHA").text = str(i.alpha_acid)
            if i.time_min:
                SubElement(he, "TIME").text = str(i.time_min)
        elif i.categoria == "yeast":
            ye = SubElement(yeasts, "YEAST")
            SubElement(ye, "NAME").text = i.nome
            SubElement(ye, "VERSION").text = "1"
            SubElement(ye, "AMOUNT").text = str(i.quantita)
            if i.attenuation:
                SubElement(ye, "ATTENUATION").text = str(i.attenuation)
        elif i.categoria == "misc":
            me = SubElement(miscs, "MISC")
            SubElement(me, "NAME").text = i.nome
            SubElement(me, "VERSION").text = "1"
            SubElement(me, "AMOUNT").text = str(i.quantita)
            if i.time_min:
                SubElement(me, "TIME").text = str(i.time_min)

    xml_str = minidom.parseString(tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    return Response(
        content=xml_str,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{ricetta.nome}.xml"'},
    )
