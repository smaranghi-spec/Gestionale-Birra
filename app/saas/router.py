"""
Router SaaS: registrazione birrificio, abbonamenti Stripe, pagine legali, accise UTF, PWA.
"""
import os
import secrets
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from . import stripe_client, tenancy
from .middleware import invalidate
from .tenancy import FREE_MAX_RICETTE, PIANI, PLATFORM_TENANT_ID, Tenant

router = APIRouter()
templates = Jinja2Templates(directory="templates")

TERMINI_VERSIONE = "2026-11"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def legal_info() -> dict:
    """Dati del titolare del servizio (da configurare come variabili d'ambiente su Render)."""
    def v(k, default="[da compilare]"):
        return os.environ.get(k, "").strip() or default
    return {
        "ragione_sociale": v("LEGAL_RAGIONE_SOCIALE"),
        "piva": v("LEGAL_PIVA"),
        "sede": v("LEGAL_SEDE"),
        "email": v("LEGAL_EMAIL"),
        "pec": v("LEGAL_PEC"),
        "nome_servizio": v("LEGAL_NOME_SERVIZIO", "BrewDesk"),
        "versione": TERMINI_VERSIONE,
        "configurato": bool(os.environ.get("LEGAL_RAGIONE_SOCIALE") and os.environ.get("LEGAL_PIVA")),
    }


def _tenant_corrente(db: Session):
    ctx = tenancy.get_current()
    if not ctx:
        return None
    with tenancy.system_context():
        return db.query(Tenant).filter(Tenant.id == ctx.id).first()


# ── REGISTRAZIONE SELF-SERVICE ───────────────────────────────────────────────

_SIGNUP_IP: dict[str, list[float]] = {}


def _signup_limited(ip: str) -> bool:
    now = time.time()
    lst = [t for t in _SIGNUP_IP.get(ip, []) if now - t < 3600]
    _SIGNUP_IP[ip] = lst
    return len(lst) >= 5


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):
    return templates.TemplateResponse(request, "saas_signup.html", {"errore": None, "legal": legal_info(), "form": {}})


@router.post("/signup")
def signup(
    request: Request,
    nome_birrificio: str = Form(...),
    email: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    conferma_password: str = Form(...),
    accetto_termini: str = Form(None),
    maggiorenne: str = Form(None),
    db: Session = Depends(get_db),
):
    from ..models import User
    form = {"nome_birrificio": nome_birrificio, "email": email, "username": username}

    def err(msg):
        return templates.TemplateResponse(request, "saas_signup.html",
                                          {"errore": msg, "legal": legal_info(), "form": form}, status_code=400)

    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    if _signup_limited(ip):
        return err("Troppe registrazioni da questa rete. Riprova tra un'ora.")
    username = username.strip()
    email = email.strip().lower()
    if not accetto_termini or not maggiorenne:
        return err("Per registrarti devi accettare Termini e Privacy e dichiarare di essere maggiorenne.")
    if len(username) < 3 or not username.replace("_", "").replace(".", "").replace("-", "").isalnum():
        return err("Username non valido (min 3 caratteri: lettere, numeri, . _ -).")
    if "@" not in email or "." not in email.split("@")[-1]:
        return err("Indirizzo email non valido.")
    if len(password) < 8:
        return err("La password deve avere almeno 8 caratteri.")
    if password != conferma_password:
        return err("Le password non coincidono.")

    with tenancy.system_context():
        if db.query(User).filter(User.username == username).first():
            return err("Username già in uso. Scegline un altro.")
        if db.query(Tenant).filter(Tenant.email == email).first():
            return err("Esiste già un account con questa email.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        t = Tenant(nome=nome_birrificio.strip()[:120], email=email, piano="free", stato_abbonamento="free",
                   iot_token=secrets.token_urlsafe(18), consenso_termini_at=now, consenso_versione=TERMINI_VERSIONE)
        db.add(t)
        db.flush()
        u = User(username=username, password_hash=User.hash_pw(password), nome=nome_birrificio.strip()[:120],
                 ruolo="admin", is_active=True, created_at=now)
        u.tenant_id = t.id
        db.add(u)
        db.commit()
        db.refresh(u)
        tid = t.id

    _SIGNUP_IP.setdefault(ip, []).append(time.time())
    request.session.clear()
    request.session.update({"user_id": u.id, "username": u.username, "nome": u.nome,
                            "ruolo": "admin", "tenant_id": tid})
    return RedirectResponse("/?msg=Benvenuto!+Il+tuo+birrificio+è+pronto", status_code=303)


# ── ABBONAMENTO ──────────────────────────────────────────────────────────────

@router.get("/abbonamento", response_class=HTMLResponse)
def abbonamento(request: Request, richiesto: str = None, limite: str = None, esito: str = None,
                db: Session = Depends(get_db)):
    from ..models import Ricetta
    t = _tenant_corrente(db)
    n_ricette = db.query(Ricetta).count()
    return templates.TemplateResponse(request, "saas_abbonamento.html", {
        "session": request.session,
        "tenant": t,
        "is_platform": bool(t and t.id == PLATFORM_TENANT_ID),
        "piani": PIANI,
        "n_ricette": n_ricette,
        "max_free": FREE_MAX_RICETTE,
        "richiesto": richiesto,
        "limite": limite,
        "esito": esito,
        "stripe_ok": stripe_client.configured(),
        "legal": legal_info(),
        "base_url": stripe_client.base_url(request),
    })


@router.post("/abbonamento/checkout")
def abbonamento_checkout(request: Request, piano: str = Form(...), accetto_termini: str = Form(None),
                         db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/abbonamento?esito=solo_admin", status_code=303)
    if piano not in ("pro", "b2b"):
        return RedirectResponse("/abbonamento", status_code=303)
    if not accetto_termini:
        return RedirectResponse("/abbonamento?esito=consenso", status_code=303)
    if not stripe_client.configured() or not stripe_client.price_for(piano):
        return RedirectResponse("/abbonamento?esito=non_attivo", status_code=303)
    t = _tenant_corrente(db)
    if not t or t.id == PLATFORM_TENANT_ID:
        return RedirectResponse("/abbonamento", status_code=303)
    try:
        url = stripe_client.create_checkout_session(t, piano, stripe_client.base_url(request))
    except Exception as e:
        print(f"[stripe] checkout error: {e}", flush=True)
        return RedirectResponse("/abbonamento?esito=errore", status_code=303)
    return RedirectResponse(url, status_code=303)


@router.post("/abbonamento/portale")
def abbonamento_portale(request: Request, db: Session = Depends(get_db)):
    t = _tenant_corrente(db)
    if request.session.get("ruolo") != "admin" or not t or not t.stripe_customer_id or not stripe_client.configured():
        return RedirectResponse("/abbonamento", status_code=303)
    try:
        url = stripe_client.create_portal_session(t.stripe_customer_id, stripe_client.base_url(request) + "/abbonamento")
    except Exception as e:
        print(f"[stripe] portal error: {e}", flush=True)
        return RedirectResponse("/abbonamento?esito=errore", status_code=303)
    return RedirectResponse(url, status_code=303)


@router.post("/abbonamento/iot-token")
def rigenera_iot_token(request: Request, db: Session = Depends(get_db)):
    t = _tenant_corrente(db)
    if request.session.get("ruolo") == "admin" and t:
        t.iot_token = secrets.token_urlsafe(18)
        db.commit()
    return RedirectResponse("/abbonamento?esito=token", status_code=303)


@router.get("/saas/stato")
def saas_stato(db: Session = Depends(get_db)):
    from ..models import Ricetta
    ctx = tenancy.get_current()
    if not ctx:
        return JSONResponse({"autenticato": False})
    n = db.query(Ricetta).count()
    illimitato = ctx.livello >= 1
    return {
        "autenticato": True,
        "piano": "platform" if ctx.is_platform else ctx.piano,
        "piano_nome": "Fondatore" if ctx.is_platform else PIANI.get(ctx.piano, PIANI["free"])["nome"],
        "n_ricette": n,
        "max_ricette": None if illimitato else FREE_MAX_RICETTE,
        "limite_raggiunto": (not illimitato) and n >= FREE_MAX_RICETTE,
        "b2b": ctx.livello >= 2,
    }


# ── WEBHOOK STRIPE ───────────────────────────────────────────────────────────

def _apply_subscription(db: Session, tenant: Tenant, sub: dict, piano_hint: str = None):
    status = sub.get("status", "")
    piano = (sub.get("metadata") or {}).get("piano") or piano_hint or tenant.piano
    tenant.stripe_subscription_id = sub.get("id") or tenant.stripe_subscription_id
    if sub.get("customer"):
        tenant.stripe_customer_id = sub["customer"]
    tenant.stato_abbonamento = status
    if status in ("active", "trialing", "past_due"):
        tenant.piano = piano if piano in ("pro", "b2b") else tenant.piano
    else:
        tenant.piano = "free"
    cpe = sub.get("current_period_end") or ((sub.get("items") or {}).get("data") or [{}])[0].get("current_period_end")
    if cpe:
        tenant.scadenza = datetime.fromtimestamp(int(cpe)).strftime("%Y-%m-%d")


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    try:
        evt = stripe_client.verify_webhook(payload, request.headers.get("stripe-signature", ""))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    etype = evt.get("type", "")
    obj = (evt.get("data") or {}).get("object") or {}
    db = SessionLocal()
    try:
        with tenancy.system_context():
            tenant = None
            tid = (obj.get("metadata") or {}).get("tenant_id") or obj.get("client_reference_id")
            if tid and str(tid).isdigit():
                tenant = db.query(Tenant).filter(Tenant.id == int(tid)).first()
            if not tenant and obj.get("customer"):
                tenant = db.query(Tenant).filter(Tenant.stripe_customer_id == obj["customer"]).first()
            if not tenant or tenant.id == PLATFORM_TENANT_ID:
                return {"received": True, "ignored": True}

            if etype == "checkout.session.completed" and obj.get("mode") == "subscription":
                tenant.stripe_customer_id = obj.get("customer") or tenant.stripe_customer_id
                tenant.stripe_subscription_id = obj.get("subscription") or tenant.stripe_subscription_id
                piano = (obj.get("metadata") or {}).get("piano")
                if piano in ("pro", "b2b") and obj.get("payment_status") in ("paid", "no_payment_required"):
                    tenant.piano = piano
                    tenant.stato_abbonamento = "active"
            elif etype in ("customer.subscription.created", "customer.subscription.updated",
                           "customer.subscription.deleted"):
                if etype.endswith("deleted"):
                    obj = dict(obj, status="canceled")
                _apply_subscription(db, tenant, obj)
            elif etype == "invoice.payment_failed":
                tenant.stato_abbonamento = "past_due"
            db.commit()
            invalidate(tenant.id)
    finally:
        db.close()
    return {"received": True}


# ── PAGINE LEGALI ────────────────────────────────────────────────────────────

@router.get("/termini", response_class=HTMLResponse)
def termini(request: Request):
    return templates.TemplateResponse(request, "saas_termini.html", {"legal": legal_info(), "piani": PIANI,
                                                                      "max_free": FREE_MAX_RICETTE})


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse(request, "saas_privacy.html", {"legal": legal_info()})


# ── ACCISE UTF (piano B2B) ───────────────────────────────────────────────────

def sg_to_plato(sg: float) -> float:
    return -616.868 + 1111.14 * sg - 630.272 * sg ** 2 + 135.997 * sg ** 3


@router.get("/accise", response_class=HTMLResponse)
def accise(request: Request, mese: str = None, aliquota: float = 2.98, riduzione: float = 40.0,
           db: Session = Depends(get_db)):
    from ..models import Cotta
    mese = mese or datetime.now().strftime("%Y-%m")
    cotte = db.query(Cotta).filter(Cotta.data_brew.like(f"{mese}%")).order_by(Cotta.data_brew).all()
    righe, tot_hl, tot_acc = [], 0.0, 0.0
    for c in cotte:
        litri = c.volume_imbottigliato or c.volume_post_bollitura or (c.ricetta.volume_target_litri if c.ricetta else None)
        og = c.og_reale or (getattr(c.ricetta, "og_target", None) if c.ricetta else None)
        if not litri or not og:
            righe.append({"c": c, "litri": litri, "plato": None, "accisa": None})
            continue
        plato = round(sg_to_plato(float(og)), 1)
        hl = float(litri) / 100.0
        acc = hl * plato * aliquota * (1 - riduzione / 100.0)
        tot_hl += hl
        tot_acc += acc
        righe.append({"c": c, "litri": litri, "plato": plato, "accisa": acc})
    return templates.TemplateResponse(request, "saas_accise.html", {
        "session": request.session, "mese": mese, "aliquota": aliquota, "riduzione": riduzione,
        "righe": righe, "tot_hl": tot_hl, "tot_acc": tot_acc,
    })


# ── PWA ──────────────────────────────────────────────────────────────────────

@router.get("/manifest.webmanifest")
def manifest():
    return FileResponse("static/manifest.webmanifest", media_type="application/manifest+json")


@router.get("/sw.js")
def service_worker():
    return FileResponse("static/sw.js", media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"})


@router.get("/offline", response_class=HTMLResponse)
def offline(request: Request):
    return templates.TemplateResponse(request, "saas_offline.html", {})
