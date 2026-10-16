import logging
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import CatalogoIngrediente, IngredienteRicetta
from ..data_catalogo import TUTTO
from ..stats import srm_to_hex

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.globals["srm_to_hex"] = srm_to_hex
logger = logging.getLogger("catalogo")


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.get("/catalogo")
def redirect_catalogo():
    return RedirectResponse("/catalogo/ingredienti", status_code=303)


@router.get("/catalogo/ingredienti", response_class=HTMLResponse)
def lista_catalogo(
    request: Request,
    categoria: str = None,
    msg: str = None,
    db: Session = Depends(get_db),
):
    try:
        all_items = db.query(CatalogoIngrediente).all()
    except Exception as e:
        logger.error(f"Errore caricamento catalogo: {e}")
        db.rollback()
        all_items = []

    per_cat = {}
    for i in all_items:
        cat = getattr(i, "categoria", None) or "misc"
        per_cat[cat] = per_cat.get(cat, 0) + 1

    if categoria:
        items = [i for i in all_items if (getattr(i, "categoria", None) or "") == categoria]
    else:
        items = all_items

    items = sorted(items, key=lambda i: (getattr(i, "nome", "") or "").lower())

    context = {
        "request": request,
        "session": request.session,
        "items": items,
        "categoria_attiva": categoria,
        "msg": msg,
        "per_cat": per_cat,
        "totale": len(all_items),
        "ricetta_id": None,
    }

    return templates.TemplateResponse(
        request,
        "catalogo_ingredienti.html",
        context,
    )


@router.get("/catalogo/ingredienti/nuovo", response_class=HTMLResponse)
def form_nuovo_ingrediente(request: Request):
    return templates.TemplateResponse(
        request,
        "nuovo_ingrediente_catalogo.html",
        {"request": request},
    )


@router.post("/catalogo/ingredienti/nuovo")
def crea_ingrediente_catalogo(
    nome: str = Form(...),
    categoria: str = Form(...),
    fermentable_type: str = Form(None),
    yield_percent: float = Form(None),
    color_srm: float = Form(None),
    alpha_acid: float = Form(None),
    hop_use: str = Form(None),
    hop_form: str = Form(None),
    attenuation: float = Form(None),
    yeast_type: str = Form(None),
    yeast_form: str = Form(None),
    misc_type: str = Form(None),
    misc_use: str = Form(None),
    db: Session = Depends(get_db),
):
    item = CatalogoIngrediente(
        nome=nome,
        categoria=categoria,
        fermentable_type=fermentable_type or None,
        yield_percent=yield_percent,
        color_srm=color_srm,
        alpha_acid=alpha_acid,
        hop_use=hop_use or None,
        hop_form=hop_form or None,
        attenuation=attenuation,
        yeast_type=yeast_type or None,
        yeast_form=yeast_form or None,
        misc_type=misc_type or None,
        misc_use=misc_use or None,
    )
    db.add(item)
    db.commit()

    return RedirectResponse("/catalogo/ingredienti", status_code=303)


def popola_catalogo_completo(db: Session) -> int:
    """Popola il catalogo con le 260 materie prime di data_catalogo.py senza toccare o duplicare quelle esistenti."""
    from ..data_catalogo import TUTTO
    esistenti = { (i.nome or "").strip().lower() for i in db.query(CatalogoIngrediente.nome).all() }
    da_aggiungere = []
    for item_data in TUTTO:
        nome_clean = (item_data.get("nome") or "").strip().lower()
        if nome_clean and nome_clean not in esistenti:
            da_aggiungere.append(CatalogoIngrediente(**item_data))
            esistenti.add(nome_clean)
    if da_aggiungere:
        db.add_all(da_aggiungere)
        db.commit()
    return len(da_aggiungere)


@router.post("/catalogo/ingredienti/popola_completo")
@router.post("/catalogo/ingredienti/popola_demo")
def popola_demo(db: Session = Depends(get_db)):
    nuovi = popola_catalogo_completo(db)
    if nuovi > 0:
        msg = f"Catalogo+aggiornato:+aggiunte+{nuovi}+materie+prime+complete"
    else:
        msg = "Catalogo+gia+aggiornato:+tutte+le+materie+prime+sono+presenti"
    return RedirectResponse(
        f"/catalogo/ingredienti?msg={msg}",
        status_code=303,
    )


@router.get("/catalogo/ingredienti/{item_id}/duplica", response_class=HTMLResponse)
def duplica_ingrediente(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = (
        db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == item_id).first()
    )
    if not item:
        return RedirectResponse("/catalogo/ingredienti", status_code=303)

    return templates.TemplateResponse(
        request,
        "duplica_ingrediente_catalogo.html",
        {
            "request": request,
            "item": item,
        },
    )


@router.post("/catalogo/ingredienti/{item_id}/aggiungi_a_ricetta/{ricetta_id}")
def aggiungi_a_ricetta(
    item_id: int,
    ricetta_id: int,
    quantita: float = Form(...),
    unita: str = Form(...),
    time_min: int = Form(None),
    note: str = Form(None),
    db: Session = Depends(get_db),
):
    item = (
        db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == item_id).first()
    )
    if not item:
        return RedirectResponse(f"/ricette/{ricetta_id}/catalogo", status_code=303)

    ing = IngredienteRicetta(
        ricetta_id=ricetta_id,
        nome=item.nome,
        categoria=item.categoria,
        quantita=quantita,
        unita=unita,
        note=note or None,
        time_min=time_min,
        fermentable_type=item.fermentable_type,
        yield_percent=item.yield_percent,
        color_srm=item.color_srm,
        alpha_acid=item.alpha_acid,
        hop_use=item.hop_use,
        hop_form=item.hop_form,
        attenuation=item.attenuation,
        yeast_type=item.yeast_type,
        yeast_form=item.yeast_form,
        misc_type=item.misc_type,
        misc_use=item.misc_use,
    )
    db.add(ing)
    db.commit()

    return RedirectResponse(f"/ricette/{ricetta_id}", status_code=303)


@router.post("/catalogo/ingredienti/{item_id}/elimina")
def elimina_ingrediente(item_id: int, db: Session = Depends(get_db)):
    item = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == item_id).first()
    if item:
        try:
            db.delete(item)
            db.commit()
        except Exception:
            db.rollback()
            return RedirectResponse("/catalogo/ingredienti?msg=Impossibile+eliminare:+elemento+in+uso", status_code=303)
    return RedirectResponse("/catalogo/ingredienti", status_code=303)
