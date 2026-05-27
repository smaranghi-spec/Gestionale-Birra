import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import IngredienteRicetta, Ricetta

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _txt(el, tag, default=""):
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else default


def _flt(el, tag, default=None):
    v = _txt(el, tag)
    try:
        return float(v) if v else default
    except ValueError:
        return default


def _int_v(el, tag, default=None):
    v = _txt(el, tag)
    try:
        return int(float(v)) if v else default
    except ValueError:
        return default


def _parse_beerxml(content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    results = []

    for recipe_el in root.iter("RECIPE"):
        r = {
            "nome": _txt(recipe_el, "NAME", "Senza nome"),
            "tipo": _txt(recipe_el, "TYPE", "All Grain"),
            "volume_target_litri": _flt(recipe_el, "BATCH_SIZE") or 20.0,
            "efficienza": _flt(recipe_el, "EFFICIENCY") or 75.0,
            "versione": _int_v(recipe_el, "VERSION") or 1,
            "note": _txt(recipe_el, "NOTES"),
            "ingredienti": [],
        }

        for f in recipe_el.iter("FERMENTABLE"):
            amount = _flt(f, "AMOUNT") or 0.0
            r["ingredienti"].append(
                {
                    "nome": _txt(f, "NAME", "Malt"),
                    "categoria": "grain",
                    "quantita": amount,
                    "unita": "kg",
                    "fermentable_type": _txt(f, "TYPE"),
                    "yield_percent": _flt(f, "YIELD"),
                    "color_srm": _flt(f, "COLOR"),
                }
            )

        for h in recipe_el.iter("HOP"):
            amount_kg = _flt(h, "AMOUNT") or 0.0
            r["ingredienti"].append(
                {
                    "nome": _txt(h, "NAME", "Hop"),
                    "categoria": "hop",
                    "quantita": round(amount_kg * 1000, 1),
                    "unita": "g",
                    "alpha_acid": _flt(h, "ALPHA"),
                    "hop_use": _txt(h, "USE"),
                    "hop_form": _txt(h, "FORM"),
                    "time_min": _int_v(h, "TIME"),
                }
            )

        for y in recipe_el.iter("YEAST"):
            r["ingredienti"].append(
                {
                    "nome": _txt(y, "NAME", "Yeast"),
                    "categoria": "yeast",
                    "quantita": _flt(y, "AMOUNT") or 1.0,
                    "unita": "pz",
                    "attenuation": _flt(y, "ATTENUATION"),
                    "yeast_type": _txt(y, "TYPE"),
                    "yeast_form": _txt(y, "FORM"),
                }
            )

        for m in recipe_el.iter("MISC"):
            r["ingredienti"].append(
                {
                    "nome": _txt(m, "NAME", "Misc"),
                    "categoria": "misc",
                    "quantita": _flt(m, "AMOUNT") or 0.0,
                    "unita": "g",
                    "misc_type": _txt(m, "TYPE"),
                    "misc_use": _txt(m, "USE"),
                    "time_min": _int_v(m, "TIME"),
                }
            )

        results.append(r)

    return results


@router.get("/importa/beerxml", response_class=HTMLResponse)
def form_importa(request: Request):
    return templates.TemplateResponse(
        "importa_beerxml.html",
        {"request": request},
    )


@router.post("/importa/beerxml")
async def importa_beerxml(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()

    try:
        ricette_data = _parse_beerxml(content)
    except ET.ParseError as e:
        return templates.TemplateResponse(
            "importa_beerxml.html",
            {
                "request": request,
                "errore": f"File XML non valido: {e}",
            },
        )

    if not ricette_data:
        return templates.TemplateResponse(
            "importa_beerxml.html",
            {
                "request": request,
                "errore": "Nessuna ricetta trovata nel file.",
            },
        )

    importate = []
    for rd in ricette_data:
        ingredienti_data = rd.pop("ingredienti")
        ricetta = Ricetta(**rd)
        db.add(ricetta)
        db.flush()

        for idata in ingredienti_data:
            db.add(IngredienteRicetta(ricetta_id=ricetta.id, **idata))

        importate.append((ricetta.id, ricetta.nome))

    db.commit()

    return templates.TemplateResponse(
        "importa_beerxml.html",
        {
            "request": request,
            "importate": importate,
        },
    )
