from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from ..db import SessionLocal
from ..models import InventarioItem, CatalogoIngrediente, Ricetta, IngredienteRicetta

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CATEGORIE = ["consumabile", "non_consumabile", "ingrediente", "chimico", "packaging"]
UNITA = ["kg", "g", "L", "mL", "pz", "rotolo", "busta", "flacone", "altro"]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/inventario", response_class=HTMLResponse)
def lista(request: Request, db: Session = Depends(get_db)):
    items = db.query(InventarioItem).order_by(InventarioItem.categoria, InventarioItem.nome).all()
    sotto_soglia = [i for i in items if i.quantita_minima and i.quantita <= i.quantita_minima]
    return templates.TemplateResponse(request, "inventario.html", {
        "items": items,
        "sotto_soglia": sotto_soglia,
        "categorie": CATEGORIE,
        "unita": UNITA,
        "session": request.session,
    })


@router.post("/inventario/nuovo")
def nuovo(
    nome: str = Form(...),
    categoria: str = Form("consumabile"),
    unita: str = Form("pz"),
    quantita: float = Form(0),
    quantita_minima: float = Form(0),
    prezzo_unitario: float = Form(None),
    fornitore: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(InventarioItem(
        nome=nome, categoria=categoria, unita=unita,
        quantita=quantita, quantita_minima=quantita_minima,
        prezzo_unitario=prezzo_unitario,
        fornitore=fornitore or None,
        note=note or None,
        ultimo_aggiornamento=datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))
    db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/{iid}/aggiorna")
def aggiorna_quantita(
    iid: int,
    delta: float = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
    if item:
        item.quantita = max(0.0, (item.quantita or 0) + delta)
        item.ultimo_aggiornamento = datetime.now().strftime("%Y-%m-%d %H:%M")
        if note:
            item.note = (item.note or "") + f"\n[{datetime.now().strftime('%d/%m/%y')}] {delta:+.2f} {item.unita}: {note}"
        db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.post("/inventario/{iid}/elimina")
def elimina(iid: int, db: Session = Depends(get_db)):
    item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
    if item:
        db.delete(item)
        db.commit()
    return RedirectResponse("/inventario", status_code=303)


@router.get("/inventario/{iid}/aggiungi-a-ricetta", response_class=HTMLResponse)
def aggiungi_a_ricetta_form(iid: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
    if not item:
        return RedirectResponse("/inventario", status_code=303)
    ricette = db.query(Ricetta).order_by(Ricetta.nome).all()
    return templates.TemplateResponse(request, "inv_aggiungi_ricetta.html", {
        "item": item,
        "ricette": ricette,
        "session": request.session,
    })


@router.post("/inventario/{iid}/aggiungi-a-ricetta")
def aggiungi_a_ricetta(
    iid: int,
    ricetta_id: int = Form(...),
    quantita: float = Form(...),
    unita: str = Form("kg"),
    db: Session = Depends(get_db),
):
    item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
    if not item:
        return RedirectResponse("/inventario", status_code=303)

    cat_map = {"ingrediente": "misc", "consumabile": "misc", "packaging": "misc", "chimico": "misc"}
    db.add(IngredienteRicetta(
        ricetta_id=ricetta_id,
        nome=item.nome,
        categoria=cat_map.get(item.categoria, "misc"),
        quantita=quantita,
        unita=unita,
        prezzo_unitario=item.prezzo_unitario,
    ))
    db.commit()
    return RedirectResponse(f"/ricette/{ricetta_id}?msg=Ingrediente+aggiunto", status_code=303)


@router.get("/inventario/da-catalogo/{ing_id}")
def da_catalogo(ing_id: int, db: Session = Depends(get_db)):
    """Aggiunge un ingrediente dal catalogo all'inventario (0 quantità da definire)."""
    ing = db.query(CatalogoIngrediente).filter(CatalogoIngrediente.id == ing_id).first()
    if not ing:
        return RedirectResponse("/inventario?msg=Ingrediente+non+trovato", status_code=303)
    existing = db.query(InventarioItem).filter(InventarioItem.nome.ilike(ing.nome)).first()
    if existing:
        return RedirectResponse(f"/inventario?msg={ing.nome.replace(' ','+')}+già+in+magazzino", status_code=303)
    cat_map = {"grain": "ingrediente", "hop": "ingrediente", "yeast": "ingrediente", "misc": "ingrediente"}
    db.add(InventarioItem(
        nome=ing.nome,
        categoria=cat_map.get(ing.categoria, "consumabile"),
        unita="kg" if ing.categoria in ("grain", "hop") else "pz" if ing.categoria == "yeast" else "g",
        quantita=0.0,
        quantita_minima=0.0,
        ultimo_aggiornamento=datetime.now().strftime("%Y-%m-%d %H:%M"),
    ))
    db.commit()
    return RedirectResponse(f"/inventario?msg={ing.nome.replace(' ','+')}+aggiunto+al+magazzino", status_code=303)


@router.get("/inventario/fisico", response_class=HTMLResponse)
def inventario_fisico(request: Request, db: Session = Depends(get_db)):
    """Pagina per conteggio fisico: mostra tutto l'inventario con input quantità."""
    items = db.query(InventarioItem).order_by(InventarioItem.categoria, InventarioItem.nome).all()
    return templates.TemplateResponse(request, "inventario_fisico.html", {
        "items": items,
        "categorie": CATEGORIE,
        "session": request.session,
    })


@router.post("/inventario/fisico/salva")
async def salva_fisico(request: Request, db: Session = Depends(get_db)):
    """Salva le quantità dal conteggio fisico."""
    form_data = await request.form()
    aggiornati = 0
    for key, val in form_data.items():
        if key.startswith("qty_"):
            try:
                iid = int(key.split("_")[1])
                nuova_qty = float(val)
            except (ValueError, IndexError):
                continue
            item = db.query(InventarioItem).filter(InventarioItem.id == iid).first()
            if item and abs(nuova_qty - (item.quantita or 0)) > 0.001:
                item.quantita = max(0.0, nuova_qty)
                item.ultimo_aggiornamento = datetime.now().strftime("%Y-%m-%d %H:%M")
                aggiornati += 1
    db.commit()
    return RedirectResponse(f"/inventario?msg=Inventario+fisico+aggiornato+({aggiornati}+voci)", status_code=303)


@router.post("/inventario/da-fattura")
def importa_da_fattura(
    data_json: str = Form("[]"),
    fornitore: str = Form(""),
    db: Session = Depends(get_db),
):
    import json
    try:
        righe = json.loads(data_json)
    except Exception:
        return RedirectResponse("/inventario?msg=Errore+JSON", status_code=303)

    importati = 0
    for r in righe:
        desc = (r.get("descrizione") or "").strip()
        if not desc:
            continue
        qty = float(r.get("quantita") or 0)
        unita = (r.get("unita") or "pz").strip()
        pu = float(r.get("prezzo_unitario") or 0)
        existing = db.query(InventarioItem).filter(
            InventarioItem.nome.ilike(f"%{desc[:30]}%")
        ).first()
        if existing:
            existing.quantita = (existing.quantita or 0) + qty
            existing.ultimo_aggiornamento = datetime.now().strftime("%Y-%m-%d %H:%M")
            if fornitore and not existing.fornitore:
                existing.fornitore = fornitore
        else:
            db.add(InventarioItem(
                nome=desc,
                categoria="ingrediente",
                unita=unita,
                quantita=qty,
                quantita_minima=0,
                prezzo_unitario=pu if pu > 0 else None,
                fornitore=fornitore or None,
                ultimo_aggiornamento=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ))
        importati += 1
    db.commit()
    return RedirectResponse(f"/inventario?msg=Importati+{importati}+articoli+da+fattura", status_code=303)
