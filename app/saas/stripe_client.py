"""
Client Stripe minimale via REST (nessuna dipendenza aggiuntiva).

Variabili d'ambiente:
  STRIPE_SECRET_KEY      sk_live_... / sk_test_...
  STRIPE_WEBHOOK_SECRET  whsec_...
  STRIPE_PRICE_PRO       price_... (abbonamento annuale 14,90 €)
  STRIPE_PRICE_B2B       price_... (abbonamento mensile 29,00 €)
  APP_BASE_URL           https://gestionale-birra.onrender.com
Se le chiavi non sono configurate, l'app funziona normalmente e i pulsanti di pagamento
mostrano "Pagamenti in attivazione".
"""
import hashlib
import hmac
import json
import os
import time

import requests

API = "https://api.stripe.com/v1"


def configured() -> bool:
    return bool(os.environ.get("STRIPE_SECRET_KEY"))


def price_for(piano: str) -> str:
    return os.environ.get({"pro": "STRIPE_PRICE_PRO", "b2b": "STRIPE_PRICE_B2B"}.get(piano, ""), "")


def base_url(request=None) -> str:
    env = os.environ.get("APP_BASE_URL", "").rstrip("/")
    if env:
        return env
    if request is not None:
        return str(request.base_url).rstrip("/")
    return ""


def _post(path: str, data: dict) -> dict:
    r = requests.post(f"{API}{path}", data=data, auth=(os.environ["STRIPE_SECRET_KEY"], ""), timeout=20)
    payload = r.json()
    if r.status_code >= 400:
        raise RuntimeError(payload.get("error", {}).get("message", "Errore Stripe"))
    return payload


def create_checkout_session(tenant, piano: str, base: str) -> str:
    data = {
        "mode": "subscription",
        "line_items[0][price]": price_for(piano),
        "line_items[0][quantity]": "1",
        "client_reference_id": str(tenant.id),
        "metadata[tenant_id]": str(tenant.id),
        "metadata[piano]": piano,
        "subscription_data[metadata][tenant_id]": str(tenant.id),
        "subscription_data[metadata][piano]": piano,
        "success_url": f"{base}/abbonamento?esito=ok",
        "cancel_url": f"{base}/abbonamento?esito=annullato",
        "allow_promotion_codes": "true",
        "billing_address_collection": "required",
        "tax_id_collection[enabled]": "true",
        "locale": "it",
    }
    if tenant.stripe_customer_id:
        data["customer"] = tenant.stripe_customer_id
        data["customer_update[address]"] = "auto"
        data["customer_update[name]"] = "auto"
    elif tenant.email:
        data["customer_email"] = tenant.email
    return _post("/checkout/sessions", data)["url"]


def create_portal_session(customer_id: str, return_url: str) -> str:
    return _post("/billing_portal/sessions", {"customer": customer_id, "return_url": return_url})["url"]


def verify_webhook(payload: bytes, sig_header: str, tolerance: int = 300) -> dict:
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise ValueError("Webhook secret non configurato")
    parts = dict(p.split("=", 1) for p in (sig_header or "").split(",") if "=" in p)
    ts = parts.get("t")
    sigs = [p.split("=", 1)[1] for p in (sig_header or "").split(",") if p.startswith("v1=")]
    if not ts or not sigs:
        raise ValueError("Firma mancante")
    if abs(time.time() - int(ts)) > tolerance:
        raise ValueError("Timestamp fuori tolleranza")
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        raise ValueError("Firma non valida")
    return json.loads(payload)
