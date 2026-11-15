"""
Gestione profilo impianto birrificio (es. BrewMonk B50).
Calcola volumi, efficienza e parametri di cotta basati sul profilo selezionato.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import ProfiloBirrificio

router = APIRouter()
templates = Jinja2Templates(directory="templates")

BREWMONK_B50 = {
    "nome": "BrewMonk B50",
    "marca": "BrewMonk",
    "modello": "B50",
    "vol_batch_litri": 50.0,
    "vol_preboil_litri": 57.0,
    "vol_mash_litri": 67.0,
    "dead_space_litri": 3.5,
    "mash_tun_deadspace_litri": 3.5,
    "boil_off_litri_ora": 3.5,
    "trub_loss_litri": 2.0,
    "assorbimento_grani_l_kg": 0.90,
    "rapporto_mash_l_kg": 3.0,
    "contrazione_termica_pct": 4.0,
    "perdita_bollitura_pct": 7.0,
    "efficienza_default": 72.0,
    "durata_bollitura_min": 60,
    "note": (
        "BrewMonk B50 — Sistema All-in-One Inox 304 da 50L con cestello malti telescopico e pompa di ricircolo integrata. "
        "Dead space sotto falso fondo: 3.5L, Boil-off: 3.5 L/h, Trub loss: 2.0L, Efficienza tipica: 72%."
    ),
}

PRESETS_IMPIANTO = {
    "b50": BREWMONK_B50,
    "g40": {
        "nome": "Grainfather G40",
        "marca": "Grainfather",
        "modello": "G40",
        "vol_batch_litri": 38.0,
        "vol_preboil_litri": 43.0,
        "vol_mash_litri": 46.0,
        "dead_space_litri": 2.0,
        "mash_tun_deadspace_litri": 2.0,
        "boil_off_litri_ora": 3.0,
        "trub_loss_litri": 2.0,
        "assorbimento_grani_l_kg": 0.85,
        "rapporto_mash_l_kg": 2.8,
        "contrazione_termica_pct": 4.0,
        "perdita_bollitura_pct": 7.0,
        "efficienza_default": 76.0,
        "durata_bollitura_min": 60,
        "note": "Grainfather G40 — All-in-One 40L con fondo conico e scambiatore controflusso.",
    },
    "bm20": {
        "nome": "Speidel Braumeister 20L",
        "marca": "Speidel",
        "modello": "BM20",
        "vol_batch_litri": 20.0,
        "vol_preboil_litri": 24.0,
        "vol_mash_litri": 28.0,
        "dead_space_litri": 1.5,
        "mash_tun_deadspace_litri": 1.5,
        "boil_off_litri_ora": 2.5,
        "trub_loss_litri": 1.5,
        "assorbimento_grani_l_kg": 0.90,
        "rapporto_mash_l_kg": 3.5,
        "contrazione_termica_pct": 4.0,
        "perdita_bollitura_pct": 8.0,
        "efficienza_default": 74.0,
        "durata_bollitura_min": 60,
        "note": "Speidel Braumeister 20L — Flusso RIMS inverso dal basso verso l'alto.",
    },
    "herms50": {
        "nome": "Impianto 3 Tini HERMS 50L Inox",
        "marca": "Custom Inox 304",
        "modello": "3T-HERMS-50",
        "vol_batch_litri": 50.0,
        "vol_preboil_litri": 58.0,
        "vol_mash_litri": 70.0,
        "dead_space_litri": 2.5,
        "mash_tun_deadspace_litri": 2.5,
        "boil_off_litri_ora": 4.5,
        "trub_loss_litri": 2.5,
        "assorbimento_grani_l_kg": 0.96,
        "rapporto_mash_l_kg": 3.0,
        "contrazione_termica_pct": 4.0,
        "perdita_bollitura_pct": 8.0,
        "efficienza_default": 78.0,
        "durata_bollitura_min": 60,
        "note": "Sistema classico 3 Tini Inox (HLT + Mash Tun con serpentina HERMS + Boil Kettle con Whirlpool e scambiatore 40 piastre).",
    },
    "pro100": {
        "nome": "Nano-Birrificio 100L Tri-Clamp",
        "marca": "Polsinelli / Custom",
        "modello": "TC-100L",
        "vol_batch_litri": 100.0,
        "vol_preboil_litri": 115.0,
        "vol_mash_litri": 135.0,
        "dead_space_litri": 4.0,
        "mash_tun_deadspace_litri": 4.0,
        "boil_off_litri_ora": 8.0,
        "trub_loss_litri": 4.5,
        "assorbimento_grani_l_kg": 0.96,
        "rapporto_mash_l_kg": 3.0,
        "contrazione_termica_pct": 4.0,
        "perdita_bollitura_pct": 7.5,
        "efficienza_default": 80.0,
        "durata_bollitura_min": 60,
        "note": "Impianto pilota da 100L con valvole a farfalla Tri-Clamp 1.5\", agitatore motorizzato e pompa magnetica Inox.",
    },
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/impianto", response_class=HTMLResponse)
def lista(request: Request, msg: str = None, db: Session = Depends(get_db)):
    profili = db.query(ProfiloBirrificio).order_by(ProfiloBirrificio.is_principale.desc(), ProfiloBirrificio.nome).all()
    principale = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.is_principale == True).first()
    return templates.TemplateResponse(request, "impianto.html", {
        "profili": profili,
        "principale": principale,
        "msg": msg,
        "session": request.session,
    })


@router.post("/impianto/nuovo")
def nuovo_profilo(
    nome: str = Form(...),
    marca: str = Form(""),
    modello: str = Form(""),
    vol_batch_litri: float = Form(50.0),
    vol_preboil_litri: float = Form(57.0),
    vol_mash_litri: float = Form(67.0),
    dead_space_litri: float = Form(3.5),
    mash_tun_deadspace_litri: float = Form(2.0),
    boil_off_litri_ora: float = Form(3.0),
    trub_loss_litri: float = Form(1.5),
    assorbimento_grani_l_kg: float = Form(0.96),
    rapporto_mash_l_kg: float = Form(3.0),
    contrazione_termica_pct: float = Form(4.0),
    perdita_bollitura_pct: float = Form(7.0),
    efficienza_default: float = Form(72.0),
    durata_bollitura_min: int = Form(60),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    p = ProfiloBirrificio(
        nome=nome, marca=marca or None, modello=modello or None,
        vol_batch_litri=vol_batch_litri, vol_preboil_litri=vol_preboil_litri,
        vol_mash_litri=vol_mash_litri, dead_space_litri=dead_space_litri,
        mash_tun_deadspace_litri=mash_tun_deadspace_litri,
        boil_off_litri_ora=boil_off_litri_ora,
        trub_loss_litri=trub_loss_litri,
        assorbimento_grani_l_kg=assorbimento_grani_l_kg,
        rapporto_mash_l_kg=rapporto_mash_l_kg,
        contrazione_termica_pct=contrazione_termica_pct,
        perdita_bollitura_pct=perdita_bollitura_pct,
        efficienza_default=efficienza_default,
        durata_bollitura_min=durata_bollitura_min,
        note=note or None,
    )
    db.add(p)
    db.commit()
    return RedirectResponse("/impianto?msg=Profilo+aggiunto+con+successo", status_code=303)


@router.post("/impianto/{pid}/modifica")
def modifica_profilo(
    pid: int,
    nome: str = Form(...),
    marca: str = Form(""),
    modello: str = Form(""),
    vol_batch_litri: float = Form(50.0),
    vol_preboil_litri: float = Form(57.0),
    vol_mash_litri: float = Form(67.0),
    dead_space_litri: float = Form(3.5),
    mash_tun_deadspace_litri: float = Form(2.0),
    boil_off_litri_ora: float = Form(3.0),
    trub_loss_litri: float = Form(1.5),
    assorbimento_grani_l_kg: float = Form(0.96),
    rapporto_mash_l_kg: float = Form(3.0),
    contrazione_termica_pct: float = Form(4.0),
    perdita_bollitura_pct: float = Form(7.0),
    efficienza_default: float = Form(72.0),
    durata_bollitura_min: int = Form(60),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if not p:
        return RedirectResponse("/impianto?msg=Profilo+non+trovato", status_code=303)
    p.nome = nome
    p.marca = marca or None
    p.modello = modello or None
    p.vol_batch_litri = vol_batch_litri
    p.vol_preboil_litri = vol_preboil_litri
    p.vol_mash_litri = vol_mash_litri
    p.dead_space_litri = dead_space_litri
    p.mash_tun_deadspace_litri = mash_tun_deadspace_litri
    p.boil_off_litri_ora = boil_off_litri_ora
    p.trub_loss_litri = trub_loss_litri
    p.assorbimento_grani_l_kg = assorbimento_grani_l_kg
    p.rapporto_mash_l_kg = rapporto_mash_l_kg
    p.contrazione_termica_pct = contrazione_termica_pct
    p.perdita_bollitura_pct = perdita_bollitura_pct
    p.efficienza_default = efficienza_default
    p.durata_bollitura_min = durata_bollitura_min
    p.note = note or None
    db.commit()
    return RedirectResponse("/impianto?msg=Profilo+impianto+aggiornato", status_code=303)


@router.post("/impianto/preset-b50")
def preset_b50(db: Session = Depends(get_db)):
    existing = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.modello == "B50").first()
    if existing:
        return RedirectResponse("/impianto?msg=BrewMonk+B50+già+presente", status_code=303)
    p = ProfiloBirrificio(**BREWMONK_B50)
    db.add(p)
    db.commit()
    return RedirectResponse("/impianto?msg=BrewMonk+B50+aggiunto", status_code=303)


@router.post("/impianto/preset/{preset_key}")
def aggiungi_preset(preset_key: str, db: Session = Depends(get_db)):
    data = PRESETS_IMPIANTO.get(preset_key)
    if not data:
        return RedirectResponse("/impianto?msg=Preset+non+valido", status_code=303)
    existing = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.nome == data["nome"]).first()
    if existing:
        return RedirectResponse(f"/impianto?msg={data['nome'].replace(' ', '+')}+già+presente", status_code=303)
    p = ProfiloBirrificio(**data)
    db.add(p)
    db.commit()
    return RedirectResponse(f"/impianto?msg={data['nome'].replace(' ', '+')}+aggiunto", status_code=303)


@router.post("/impianto/{pid}/imposta-principale")
def imposta_principale(pid: int, db: Session = Depends(get_db)):
    db.query(ProfiloBirrificio).update({"is_principale": False})
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if p:
        p.is_principale = True
    db.commit()
    return RedirectResponse("/impianto?msg=Impianto+principale+aggiornato", status_code=303)


@router.post("/impianto/{pid}/elimina")
def elimina(pid: int, db: Session = Depends(get_db)):
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/impianto?msg=Profilo+eliminato", status_code=303)


@router.get("/impianto/{pid}/calcola")
def calcola(pid: int, vol_batch: float = 20.0, db: Session = Depends(get_db)):
    """API JSON: dato un volume batch target, calcola tutti i volumi."""
    p = db.query(ProfiloBirrificio).filter(ProfiloBirrificio.id == pid).first()
    if not p:
        return JSONResponse({"errore": "Profilo non trovato"}, status_code=404)
    ratio = vol_batch / (p.vol_batch_litri or 50.0)
    return JSONResponse({
        "vol_batch": round(vol_batch, 1),
        "vol_preboil": round(p.vol_preboil_litri * ratio, 1),
        "vol_mash": round(p.vol_mash_litri * ratio, 1),
        "dead_space": round(p.dead_space_litri, 1),
        "perdita_bollitura_pct": p.perdita_bollitura_pct,
        "efficienza": p.efficienza_default,
        "durata_bollitura_min": p.durata_bollitura_min,
    })
