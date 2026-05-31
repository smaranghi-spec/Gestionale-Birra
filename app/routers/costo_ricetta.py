"""
Pagina costo ricetta: breakdown ingredienti, overhead, prezzo di vendita suggerito, IVA.
"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Ricetta, IngredienteRicetta, InventarioItem, Cotta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _costo_ingredienti(ingredienti: list, db: Session) -> list[dict]:
    righe = []
    for i in ingredienti:
        pu = i.prezzo_unitario or 0.0
        if pu == 0:
            inv = db.query(InventarioItem).filter(
                InventarioItem.nome.ilike(f"%{i.nome[:20]}%")
            ).first()
            if inv and inv.prezzo_unitario:
                pu = inv.prezzo_unitario
        costo = round(pu * (i.quantita or 0.0), 3)
        righe.append({
            "nome": i.nome,
            "categoria": i.categoria,
            "quantita": i.quantita,
            "unita": i.unita or "",
            "prezzo_unitario": pu,
            "costo": costo,
            "da_magazzino": (i.prezzo_unitario is None or i.prezzo_unitario == 0) and pu > 0,
        })
    return righe


@router.get("/ricette/{ricetta_id}/costo", response_class=HTMLResponse)
def costo_ricetta(
    ricetta_id: int,
    request: Request,
    overhead_pct: float = 25.0,
    markup_pct: float = 50.0,
    db: Session = Depends(get_db),
):
    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return RedirectResponse("/ricette/html", status_code=303)

    ingredienti = db.query(IngredienteRicetta).filter(
        IngredienteRicetta.ricetta_id == ricetta_id
    ).all()

    righe = _costo_ingredienti(ingredienti, db)
    costo_materie = sum(r["costo"] for r in righe)
    costo_overhead = round(costo_materie * overhead_pct / 100, 2)
    costo_totale = round(costo_materie + costo_overhead, 2)

    vol = ricetta.volume_target_litri or 20.0
    costo_per_litro = round(costo_totale / vol, 3) if vol else 0

    prezzo_senza_markup = costo_totale
    prezzo_con_markup = round(costo_totale * (1 + markup_pct / 100), 2)
    prezzo_per_litro = round(prezzo_con_markup / vol, 3) if vol else 0

    BOTTIGLIE_075 = round(vol / 0.75)
    BOTTIGLIE_033 = round(vol / 0.33)

    prezzo_bottiglia_075 = round(prezzo_con_markup / BOTTIGLIE_075, 2) if BOTTIGLIE_075 else 0
    prezzo_bottiglia_033 = round(prezzo_con_markup / BOTTIGLIE_033, 2) if BOTTIGLIE_033 else 0

    iva_scenari = []
    for aliq in [0, 4, 10, 22]:
        iva_scenari.append({
            "aliquota": aliq,
            "totale": round(prezzo_con_markup * (1 + aliq / 100), 2),
            "per_litro": round(prezzo_per_litro * (1 + aliq / 100), 3),
            "bottiglia_075": round(prezzo_bottiglia_075 * (1 + aliq / 100), 2),
            "bottiglia_033": round(prezzo_bottiglia_033 * (1 + aliq / 100), 2),
        })

    cotte = db.query(Cotta).filter(Cotta.ricetta_id == ricetta_id).order_by(Cotta.id.desc()).limit(5).all()

    return templates.TemplateResponse(request, "costo_ricetta.html", {
        "ricetta": ricetta,
        "righe": righe,
        "costo_materie": costo_materie,
        "costo_overhead": costo_overhead,
        "costo_totale": costo_totale,
        "costo_per_litro": costo_per_litro,
        "prezzo_con_markup": prezzo_con_markup,
        "prezzo_per_litro": prezzo_per_litro,
        "prezzo_bottiglia_075": prezzo_bottiglia_075,
        "prezzo_bottiglia_033": prezzo_bottiglia_033,
        "iva_scenari": iva_scenari,
        "overhead_pct": overhead_pct,
        "markup_pct": markup_pct,
        "vol": vol,
        "n_bottiglie_075": BOTTIGLIE_075,
        "n_bottiglie_033": BOTTIGLIE_033,
        "cotte": cotte,
        "session": request.session,
    })
