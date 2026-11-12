"""
Router per il Configuratore Impianti (Digital Twin, Brewery Builder)
e per il Carrello Dropshipping / Retrofit Engine.
"""
from fastapi import APIRouter, Depends, Form, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from .autobom import PORTS, risolvi_connessione
from .cart import (
    get_cart, add_to_cart, remove_from_cart, clear_cart,
    add_bom_to_cart, add_mancanti_ricetta_to_cart
)
from .stripe_client import configured as stripe_configured, base_url as get_base_url
from .tenancy import get_current

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── CONFIGURATORE IMPIANTI & RETROFIT ENGINE ────────────────────────────────

@router.get("/configuratore", response_class=HTMLResponse)
def configuratore_page(request: Request, tab: str = "builder"):
    ctx = get_current()
    is_pro = ctx.livello >= 1 if ctx else False

    return templates.TemplateResponse(request, "configuratore.html", {
        "session": request.session,
        "tab_attiva": tab,
        "is_pro": is_pro,
        "porte": PORTS,
    })

@router.post("/api/retrofit/solve")
def api_solve_retrofit(payload: dict = Body(...)):
    nodo_a = payload.get("nodo_a")
    nodo_b = payload.get("nodo_b")
    if not nodo_a or not nodo_b:
        return JSONResponse({"errore": "Specificare nodo_a e nodo_b"}, status_code=400)
    
    risultato = risolvi_connessione(nodo_a, nodo_b)
    return risultato

# ── CARRELLO DROPSHIPPING UNIFICATO & CASSA CONTINUA ───────────────────────

@router.get("/carrello", response_class=HTMLResponse)
def carrello_page(request: Request, msg: str = None):
    cart = get_cart(request)
    return templates.TemplateResponse(request, "carrello.html", {
        "session": request.session,
        "cart": cart,
        "msg": msg,
        "stripe_ok": stripe_configured(),
    })

@router.post("/carrello/aggiungi-mancanti/{ricetta_id}")
def aggiungi_mancanti_da_ricetta(ricetta_id: int, request: Request, db: Session = Depends(get_db)):
    """La Cassa Continua: invia tutti gli ingredienti mancanti della ricetta al carrello."""
    n_aggiunti = add_mancanti_ricetta_to_cart(request, db, ricetta_id)
    if n_aggiunti > 0:
        msg = f"{n_aggiunti}+ingredienti+mancanti+aggiunti+al+carrello!"
    else:
        msg = "Tutti+gli+ingredienti+sono+già+disponibili+in+magazzino!"
    return RedirectResponse(f"/carrello?msg={msg}", status_code=303)

@router.post("/carrello/aggiungi-bom")
def aggiungi_bom_al_carrello(request: Request, payload: dict = Body(...)):
    bom = payload.get("bom", {})
    count = add_bom_to_cart(request, bom)
    return {"status": "ok", "aggiunti": count, "cart": get_cart(request)}

@router.post("/carrello/rimuovi/{sku}")
def rimuovi_elemento_carrello(sku: str, request: Request):
    remove_from_cart(request, sku)
    return RedirectResponse("/carrello?msg=Articolo+rimosso", status_code=303)

@router.post("/carrello/svuota")
def svuota_carrello(request: Request):
    clear_cart(request)
    return RedirectResponse("/carrello?msg=Carrello+svuotato", status_code=303)

@router.post("/carrello/checkout")
def checkout_carrello(request: Request):
    cart = get_cart(request)
    if not cart.get("items"):
        return RedirectResponse("/carrello?msg=Il+carrello+è+vuoto", status_code=303)
    
    # Se Stripe è configurato, possiamo creare una checkout session per gli ordini hardware/consumabili
    # Altrimenti mostriamo pagina di conferma ordine simulata
    return templates.TemplateResponse(request, "carrello_conferma.html", {
        "session": request.session,
        "cart": cart,
        "base_url": get_base_url(request),
    })
