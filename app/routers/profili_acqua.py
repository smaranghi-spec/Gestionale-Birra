"""
Profili acqua di riferimento per stile.
Fornisce preset classici (Plzeň, Burton, Dublin…) e CRUD personalizzato.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import ProfiloAcquaPreset

router = APIRouter()
templates = Jinja2Templates(directory="templates")

PRESETS_DEFAULT = [
    {"nome": "Plzeň (Pilsner)", "citta": "Plzeň, CZ", "stili_consigliati": "Czech Pilsner, Bohemian Pilsner", "ca": 7, "mg": 3, "na": 2, "cl": 5, "so4": 5, "hco3": 16, "note": "Acqua molto soffice. Ideale per lager chiare e pilsner."},
    {"nome": "Burton-on-Trent", "citta": "Burton, UK", "stili_consigliati": "IPA, Pale Ale, Bitter", "ca": 295, "mg": 45, "na": 55, "cl": 25, "so4": 725, "hco3": 300, "note": "Alta solfaticità, accentua il luppolo e secchezza. Classica per IPA britannica."},
    {"nome": "London", "citta": "Londra, UK", "stili_consigliati": "Porter, Stout, Brown Ale, ESB", "ca": 52, "mg": 4, "na": 86, "cl": 34, "so4": 58, "hco3": 156, "note": "Moderatamente minerale. Esalta malti tostati e corpo pieno."},
    {"nome": "Dublin", "citta": "Dublino, IE", "stili_consigliati": "Dry Stout, Irish Stout", "ca": 118, "mg": 4, "na": 12, "cl": 19, "so4": 54, "hco3": 315, "note": "Alto bicarbonato, pH naturalmente più alto. Perfetta per stout secche."},
    {"nome": "München", "citta": "Monaco, DE", "stili_consigliati": "Helles, Märzen, Dunkel, Bock", "ca": 77, "mg": 17, "na": 4, "cl": 8, "so4": 18, "hco3": 295, "note": "Carbonatica ma bilanciata. Ottima per lager bavaresi maltate."},
    {"nome": "Vienna", "citta": "Vienna, AT", "stili_consigliati": "Vienna Lager, Märzen", "ca": 68, "mg": 11, "na": 8, "cl": 12, "so4": 53, "hco3": 120, "note": "Minerale bilanciata. Classica per Vienna Lager."},
    {"nome": "Dortmund", "citta": "Dortmund, DE", "stili_consigliati": "Dortmunder Export, Helles", "ca": 225, "mg": 40, "na": 60, "cl": 60, "so4": 120, "hco3": 180, "note": "Dura e minerale. Per Export e lager strutturate."},
    {"nome": "Edinburgh", "citta": "Edimburgo, UK", "stili_consigliati": "Scottish Ale, Wee Heavy", "ca": 100, "mg": 18, "na": 55, "cl": 50, "so4": 140, "hco3": 270, "note": "Acqua dura calcarea. Perfetta per Scottish Ale maltate."},
    {"nome": "Amsterdam", "citta": "Amsterdam, NL", "stili_consigliati": "Witbier, Weizen, Berliner", "ca": 5, "mg": 1, "na": 7, "cl": 12, "so4": 11, "hco3": 28, "note": "Acqua molto soffice. Ottima per birre di frumento e acide."},
    {"nome": "Balanced (IPA americana)", "citta": "—", "stili_consigliati": "American IPA, DIPA, Pale Ale", "ca": 100, "mg": 10, "na": 10, "cl": 75, "so4": 150, "hco3": 50, "note": "Profilo bilanciato per IPA americane. Rapporto Cl/SO4 ~1:2 per enfatizzare luppolatura."},
    {"nome": "Malt-forward", "citta": "—", "stili_consigliati": "Amber Ale, Red Ale, Scottish, Mild", "ca": 80, "mg": 10, "na": 15, "cl": 100, "so4": 50, "hco3": 100, "note": "Alto cloruro rispetto a solfato. Esalta corpo e morbidezza maltata."},
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_presets(db: Session):
    if db.query(ProfiloAcquaPreset).count() == 0:
        for p in PRESETS_DEFAULT:
            db.add(ProfiloAcquaPreset(**p))
        db.commit()


@router.get("/profili-acqua", response_class=HTMLResponse)
def lista(request: Request, msg: str = None, db: Session = Depends(get_db)):
    _seed_presets(db)
    presets = db.query(ProfiloAcquaPreset).order_by(ProfiloAcquaPreset.nome).all()
    return templates.TemplateResponse(request, "profili_acqua.html", {
        "presets": presets, "msg": msg, "session": request.session,
    })


@router.post("/profili-acqua/nuovo")
def nuovo(
    nome: str = Form(...),
    citta: str = Form(""),
    stili_consigliati: str = Form(""),
    ca: float = Form(0.0), mg: float = Form(0.0), na: float = Form(0.0),
    cl: float = Form(0.0), so4: float = Form(0.0), hco3: float = Form(0.0),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(ProfiloAcquaPreset(
        nome=nome, citta=citta or None, stili_consigliati=stili_consigliati or None,
        ca=ca, mg=mg, na=na, cl=cl, so4=so4, hco3=hco3, note=note or None,
    ))
    db.commit()
    return RedirectResponse("/profili-acqua?msg=Profilo+aggiunto", status_code=303)


@router.post("/profili-acqua/{pid}/elimina")
def elimina(pid: int, db: Session = Depends(get_db)):
    p = db.query(ProfiloAcquaPreset).filter(ProfiloAcquaPreset.id == pid).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/profili-acqua?msg=Eliminato", status_code=303)


@router.get("/profili-acqua/{pid}/json")
def preset_json(pid: int, db: Session = Depends(get_db)):
    p = db.query(ProfiloAcquaPreset).filter(ProfiloAcquaPreset.id == pid).first()
    if not p:
        return JSONResponse({"errore": "Non trovato"}, status_code=404)
    return JSONResponse({"ca": p.ca, "mg": p.mg, "na": p.na, "cl": p.cl, "so4": p.so4, "hco3": p.hco3, "nome": p.nome})


@router.get("/profili-acqua/tutti-json")
def tutti_json(db: Session = Depends(get_db)):
    _seed_presets(db)
    presets = db.query(ProfiloAcquaPreset).order_by(ProfiloAcquaPreset.nome).all()
    return JSONResponse([{
        "id": p.id, "nome": p.nome, "citta": p.citta,
        "stili": p.stili_consigliati,
        "ca": p.ca, "mg": p.mg, "na": p.na, "cl": p.cl, "so4": p.so4, "hco3": p.hco3,
    } for p in presets])
