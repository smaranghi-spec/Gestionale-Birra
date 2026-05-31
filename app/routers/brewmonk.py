import json
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import BrewMonkConfig, IngredienteRicetta, Ricetta
from .. import brewmonk_client as bmc

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_config(db: Session) -> BrewMonkConfig:
    cfg = db.query(BrewMonkConfig).first()
    if not cfg:
        cfg = BrewMonkConfig(username="", password="", attivo=False)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _build_beerxml(ricetta, ingredienti: list) -> bytes:
    root = Element("RECIPES")
    r_el = SubElement(root, "RECIPE")
    SubElement(r_el, "NAME").text = ricetta.nome
    SubElement(r_el, "VERSION").text = str(ricetta.versione or 1)
    SubElement(r_el, "TYPE").text = ricetta.tipo or "All Grain"
    SubElement(r_el, "BATCH_SIZE").text = str(ricetta.volume_target_litri or 20)
    SubElement(r_el, "EFFICIENCY").text = str(ricetta.efficienza or 75)
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
            SubElement(fe, "TYPE").text = i.fermentable_type or "Grain"
            q = i.quantita or 0
            SubElement(fe, "AMOUNT").text = str(q if i.unita == "kg" else q / 1000)
            if i.yield_percent:
                SubElement(fe, "YIELD").text = str(i.yield_percent)
            if i.color_srm:
                SubElement(fe, "COLOR").text = str(i.color_srm)
        elif i.categoria == "hop":
            he = SubElement(hops, "HOP")
            SubElement(he, "NAME").text = i.nome
            SubElement(he, "VERSION").text = "1"
            q = i.quantita or 0
            SubElement(he, "AMOUNT").text = str(q if i.unita == "kg" else q / 1000)
            if i.alpha_acid:
                SubElement(he, "ALPHA").text = str(i.alpha_acid)
            if i.time_min:
                SubElement(he, "TIME").text = str(i.time_min)
            SubElement(he, "USE").text = i.hop_use or "Boil"
            SubElement(he, "FORM").text = i.hop_form or "Pellet"
        elif i.categoria == "yeast":
            ye = SubElement(yeasts, "YEAST")
            SubElement(ye, "NAME").text = i.nome
            SubElement(ye, "VERSION").text = "1"
            q = i.quantita or 0
            SubElement(ye, "AMOUNT").text = str(q)
            SubElement(ye, "TYPE").text = i.yeast_type or "Ale"
            SubElement(ye, "FORM").text = i.yeast_form or "Dry"
            if i.attenuation:
                SubElement(ye, "ATTENUATION").text = str(i.attenuation)
        elif i.categoria == "misc":
            me = SubElement(miscs, "MISC")
            SubElement(me, "NAME").text = i.nome
            SubElement(me, "VERSION").text = "1"
            q = i.quantita or 0
            SubElement(me, "AMOUNT").text = str(q)
            SubElement(me, "TYPE").text = i.misc_type or "Other"
            SubElement(me, "USE").text = i.misc_use or "Boil"
            if i.time_min:
                SubElement(me, "TIME").text = str(i.time_min)

    xml_str = minidom.parseString(tostring(root, encoding="unicode")).toprettyxml(indent="  ")
    return xml_str.encode("utf-8")


@router.get("/brewmonk", response_class=HTMLResponse)
def dashboard(request: Request, msg: str = None, db: Session = Depends(get_db)):
    cfg = _get_config(db)
    ricette = db.query(Ricetta).order_by(Ricetta.nome).all()
    return templates.TemplateResponse(
        request,
        "brewmonk.html",
        {
            "cfg": cfg,
            "ricette": ricette,
            "msg": msg,
            "session": request.session,
        },
    )


@router.post("/brewmonk/salva-config")
def salva_config(
    username: str = Form(""),
    password: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    cfg = _get_config(db)
    cfg.username = username.strip()
    if password.strip():
        cfg.password = password.strip()
    cfg.note = note or None
    cfg.attivo = bool(cfg.username and cfg.password)
    db.commit()
    return RedirectResponse("/brewmonk?msg=Configurazione+salvata", status_code=303)


@router.get("/brewmonk/test-login")
async def test_login(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    if not cfg.username or not cfg.password:
        return JSONResponse({"ok": False, "msg": "Credenziali non configurate"})
    client = await bmc.login(cfg.username, cfg.password)
    if client:
        await client.aclose()
        return JSONResponse({"ok": True, "msg": "Login BrewMonk riuscito ✓"})
    return JSONResponse({"ok": False, "msg": "Login fallito — controlla username/password"})


@router.get("/brewmonk/stato")
async def stato_live(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    if not cfg.username or not cfg.password:
        return JSONResponse({"errore": "Credenziali non configurate"})
    client = await bmc.login(cfg.username, cfg.password)
    if not client:
        return JSONResponse({"errore": "Login fallito"})
    try:
        brew, ferm, sessions = (
            await bmc.get_brew_status(client),
            await bmc.get_ferment_status(client),
            await bmc.get_sessions(client),
        )
        cfg.ultimo_sync = datetime.now().strftime("%Y-%m-%d %H:%M")
        db.commit()
        return JSONResponse({"brew": brew, "fermentazione": ferm, "sessioni": sessions[:5]})
    finally:
        await client.aclose()


@router.get("/brewmonk/ricette-remote")
async def ricette_remote(db: Session = Depends(get_db)):
    cfg = _get_config(db)
    if not cfg.username or not cfg.password:
        return JSONResponse({"errore": "Credenziali non configurate", "ricette": []})
    client = await bmc.login(cfg.username, cfg.password)
    if not client:
        return JSONResponse({"errore": "Login fallito", "ricette": []})
    try:
        ricette = await bmc.get_recipes(client)
        return JSONResponse({"ricette": ricette})
    finally:
        await client.aclose()


@router.post("/brewmonk/push/{ricetta_id}")
async def push_ricetta(ricetta_id: int, db: Session = Depends(get_db)):
    cfg = _get_config(db)
    if not cfg.username or not cfg.password:
        return JSONResponse({"ok": False, "msg": "Credenziali non configurate"})
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return JSONResponse({"ok": False, "msg": "Ricetta non trovata"})
    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    xml_bytes = _build_beerxml(ricetta, ingredienti)
    client = await bmc.login(cfg.username, cfg.password)
    if not client:
        return JSONResponse({"ok": False, "msg": "Login BrewMonk fallito"})
    try:
        result = await bmc.push_recipe_beerxml(client, xml_bytes, ricetta.nome)
        if result["ok"]:
            cfg.ultimo_sync = datetime.now().strftime("%Y-%m-%d %H:%M")
            db.commit()
        return JSONResponse(result)
    finally:
        await client.aclose()


@router.get("/brewmonk/download-xml/{ricetta_id}")
def download_xml(ricetta_id: int, db: Session = Depends(get_db)):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return Response("Non trovata", status_code=404)
    ingredienti = db.query(IngredienteRicetta).filter(IngredienteRicetta.ricetta_id == ricetta_id).all()
    xml_bytes = _build_beerxml(ricetta, ingredienti)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{ricetta.nome}.xml"'},
    )
