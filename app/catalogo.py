from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import CatalogoIngrediente, IngredienteRicetta
from ..data_catalogo import TUTTO

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/catalogo/ingredienti", response_class=HTMLResponse)
def lista_catalogo(request: Request, categoria: str = None, msg: str = None, db: Session = Depends(get_db)):
    query = db.query(CatalogoIngrediente)
    if categoria:
        query = query.filter(CatalogoIngrediente.categoria == categoria)
    items = query.order_by(CatalogoIngrediente.nome).all()
    return templates.TemplateResponse(request, "catalogo_ingredienti.html", {
        "items": items,
        "categoria_attiva": categoria,
        "msg": msg,
    })


@router.get("/catalogo/ingredienti/nuovo", response_class=HTMLResponse)
def form_nuovo_ingrediente(request: Request):
    return templates.TemplateResponse(request, "nuovo_ingrediente_catalogo.html", {})


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


@router.post("/catalogo/ingredienti/popola_demo")
def popola_demo(db: Session = Depends(get_db)):
    esistenti = {i.nome for i in db.query(CatalogoIngrediente.nome).all()}
    nuovi = 0
    for d in TUTTO:
        if d["nome"] in esistenti:
            continue
        db.add(CatalogoIngrediente(**d))
        nuovi += 1
    db.commit()
    return RedirectResponse(f"/catalogo/ingredienti?msg=Importati+{nuovi}+ingredienti", status_code=303)


@router.get("/catalogo/ingredienti/{item_id}/duplica", response_class=HTMLResponse)
def duplica_ingrediente(item_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == item_id).first()
    if not item:
        return RedirectResponse("/catalogo/ingredienti", status_code=303)
    return templates.TemplateResponse(request, "duplica_ingrediente_catalogo.html", {"item": item})


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
    item = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == item_id).first()
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
