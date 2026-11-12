"""
Modulo Carrello Dropshipping Headless & Cassa Continua.
Gestisce l'aggregazione di:
1. Consumabili mancanti da ricetta (malt, luppoli, lieviti)
2. Hardware e distinta base (Auto-BOM e parti impianto)
"""
from typing import Dict, List, Optional
from fastapi import Request
from sqlalchemy.orm import Session

CART_SESSION_KEY = "saas_cart"

def get_cart(request: Request) -> Dict:
    """Restituisce il carrello attivo memorizzato nella sessione."""
    cart = request.session.get(CART_SESSION_KEY)
    if not isinstance(cart, dict) or "items" not in cart:
        cart = {
            "items": [],
            "articoli": [],
            "totale": 0.0,
            "totale_pezzi": 0,
            "spedizione_gratuita": False,
            "mancante_spedizione": 59.0,
        }
        request.session[CART_SESSION_KEY] = cart
    return cart

def save_cart(request: Request, cart: Dict):
    """Ricalcola totali e salva in sessione."""
    tot = 0.0
    n_pezzi = 0
    for it in cart.get("items", []):
        subtot = round(float(it.get("prezzo", 0.0)) * float(it.get("qta", 1.0)), 2)
        it["subtotale"] = subtot
        tot += subtot
        n_pezzi += int(it.get("qta", 1)) if isinstance(it.get("qta"), int) else 1
    cart["totale"] = round(tot, 2)
    cart["totale_pezzi"] = n_pezzi
    cart["articoli"] = cart.get("items", [])
    # Spedizione gratuita sopra 59€
    cart["spedizione_gratuita"] = cart["totale"] >= 59.0
    cart["mancante_spedizione"] = round(max(0.0, 59.0 - cart["totale"]), 2)
    request.session[CART_SESSION_KEY] = cart

def add_to_cart(
    request: Request,
    sku: str,
    nome: str,
    categoria: str,
    qta: float,
    unita: str,
    prezzo: float,
    dettagli: Optional[str] = None
) -> Dict:
    cart = get_cart(request)
    # Cerca se già presente per SKU
    trovato = False
    for it in cart["items"]:
        if it["sku"] == sku:
            it["qta"] = round(it["qta"] + qta, 2)
            trovato = True
            break
    if not trovato:
        cart["items"].append({
            "sku": sku,
            "nome": nome,
            "categoria": categoria,
            "qta": qta,
            "unita": unita,
            "prezzo": float(prezzo),
            "dettagli": dettagli or "",
        })
    save_cart(request, cart)
    return cart

def remove_from_cart(request: Request, sku: str) -> Dict:
    cart = get_cart(request)
    cart["items"] = [it for it in cart["items"] if it["sku"] != sku]
    save_cart(request, cart)
    return cart

def clear_cart(request: Request) -> Dict:
    cart = {"items": [], "totale": 0.0, "totale_pezzi": 0}
    save_cart(request, cart)
    return cart

def add_bom_to_cart(request: Request, bom: Dict) -> int:
    """Aggiunge una distinta base calcolata dall'Auto-BOM al carrello."""
    pezzi = bom.get("pezzi", [])
    count = 0
    for p in pezzi:
        add_to_cart(
            request=request,
            sku=p["sku"],
            nome=p["nome"],
            categoria="Hardware & Raccordi",
            qta=float(p.get("qta", 1)),
            unita="pz",
            prezzo=float(p.get("prezzo", 0.0)),
            dettagli="Distinta base Retrofit garantita"
        )
        count += 1
    return count

def add_mancanti_ricetta_to_cart(request: Request, db: Session, ricetta_id: int) -> int:
    """
    La Cassa Continua:
    Confronta i grani e luppoli della ricetta con l'inventario del birrificio;
    se c'è un gap, aggiunge esattamente le quantità mancanti al carrello.
    """
    from ..routers.ricette import _calcola_fattibilita_ricetta
    from ..models import Ricetta, InventarioItem

    ricetta = db.query(Ricetta).filter(Ricetta.id == ricetta_id).first()
    if not ricetta:
        return 0

    inv_items = db.query(InventarioItem).all()
    fattibilita = _calcola_fattibilita_ricetta(ricetta.ingredienti or [], inv_items)
    mancanti = fattibilita.get("mancanti", [])
    aggiunti = 0

    for m in mancanti:
        # Prezzo stimato di mercato per consumabili dropshipping
        cat = (m.get("categoria") or "").lower()
        prezzo_kg = 3.90 if cat in ("malt", "malto", "fermentabile") else (24.00 if cat in ("hop", "luppolo") else 4.50)
        qta_mancante = float(m.get("manca", 0.0))
        unita = (m.get("unita") or "kg").lower()
        
        # Luppoli in grammi convertiti
        if unita == "g":
            prezzo_unita = round((qta_mancante / 100.0) * (prezzo_kg / 10.0), 2)
            if prezzo_unita < 3.50:
                prezzo_unita = 3.50  # busta minima 100g
        else:
            prezzo_unita = round(qta_mancante * prezzo_kg, 2)
            if prezzo_unita < 2.50:
                prezzo_unita = 2.50

        sku = f"ING-{cat[:3].upper() if cat else 'RAW'}-{abs(hash(m['nome'])) % 10000:04d}"
        add_to_cart(
            request=request,
            sku=sku,
            nome=f"{m['nome']} ({qta_mancante} {unita})",
            categoria=f"Consumabili ({cat.capitalize() if cat else 'Ingrediente'})",
            qta=1,
            unita="conf",
            prezzo=max(2.0, prezzo_unita),
            dettagli=f"Per ricetta: {ricetta.nome}"
        )
        aggiunti += 1

    return aggiunti
