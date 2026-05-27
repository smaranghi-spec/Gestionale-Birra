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
def lista_catalogo(
    request: Request,
    categoria: str = None,
    msg: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(CatalogoIngrediente)
    if categoria:
        query = query.filter(CatalogoIngrediente.categoria == categoria)
    items = query.order_by(CatalogoIngrediente.nome).all()

    return templates.TemplateResponse(
        "catalogo_ingredienti.html",
        {
            "request": request,
            "items": items,
            "categoria_attiva": categoria,
            "msg": msg,
        },
    )


@router.get("/catalogo/ingredienti/nuovo", response_class=HTMLResponse)
def form_nuovo_ingrediente(request: Request):
    return templates.TemplateResponse(
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


@router.post("/catalogo/ingredienti/popola_demo")
def popola_demo(db: Session = Depends(get_db)):
    if db.query(CatalogoIngrediente).count() > 0:
        return RedirectResponse("/catalogo/ingredienti", status_code=303)

    demo = [
        CatalogoIngrediente(
            nome="Pale Ale Malt",
            categoria="grain",
            fermentable_type="Grain",
            yield_percent=78.0,
            color_srm=3.5,
        ),
        CatalogoIngrediente(
            nome="Pilsner Malt",
            categoria="grain",
            fermentable_type="Grain",
            yield_percent=80.0,
            color_srm=1.8,
        ),
        CatalogoIngrediente(
            nome="Munich Malt",
            categoria="grain",
            fermentable_type="Grain",
            yield_percent=77.0,
            color_srm=9.0,
        ),
        CatalogoIngrediente(
            nome="Caramel 60L",
            categoria="grain",
            fermentable_type="Crystal",
            yield_percent=72.0,
            color_srm=60.0,
        ),
        CatalogoIngrediente(
            nome="Chocolate Malt",
            categoria="grain",
            fermentable_type="Roasted",
            yield_percent=60.0,
            color_srm=350.0,
        ),
        CatalogoIngrediente(
            nome="Cascade",
            categoria="hop",
            alpha_acid=5.5,
            hop_use="Boil",
            hop_form="Pellet",
        ),
        CatalogoIngrediente(
            nome="Centennial",
            categoria="hop",
            alpha_acid=10.0,
            hop_use="Boil",
            hop_form="Pellet",
        ),
        CatalogoIngrediente(
            nome="Citra",
            categoria="hop",
            alpha_acid=12.0,
            hop_use="Dry Hop",
            hop_form="Pellet",
        ),
        CatalogoIngrediente(
            nome="Saaz",
            categoria="hop",
            alpha_acid=3.5,
            hop_use="Boil",
            hop_form="Pellet",
        ),
        CatalogoIngrediente(
            nome="Safale US-05",
            categoria="yeast",
            attenuation=77.0,
            yeast_type="Ale",
            yeast_form="Dry",
        ),
        CatalogoIngrediente(
            nome="Wyeast 1056 American Ale",
            categoria="yeast",
            attenuation=75.0,
            yeast_type="Ale",
            yeast_form="Liquid",
        ),
        CatalogoIngrediente(
            nome="Irish Moss",
            categoria="misc",
            misc_type="Fining",
            misc_use="Boil",
        ),
        CatalogoIngrediente(
            nome="Whirlfloc",
            categoria="misc",
            misc_type="Fining",
            misc_use="Boil",
        ),
    ]

    db.add_all(demo)
    db.commit()
    nuovi = len(demo)

    return RedirectResponse(
        f"/catalogo/ingredienti?msg=Importati+{nuovi}+ingredienti",
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
