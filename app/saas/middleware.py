"""
TenantMiddleware: imposta il contesto tenant per ogni richiesta e applica i limiti di piano.
"""
import hmac
import re
import time

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..db import SessionLocal
from . import tenancy
from .tenancy import PLATFORM_TENANT_ID, Tenant, TenantCtx

# Percorsi riservati alla piattaforma (backup/import completi del DB, debug)
PLATFORM_ONLY = ("/admin/export", "/admin/import", "/debug/seed-admin", "/debug/reset-admin",
                 "/amministrazione", "/brewmonk")
# Funzioni del piano B2B (tracciabilità HACCP, SOP, accise UTF)
B2B_ONLY = ("/tracciabilita", "/procedure", "/accise")

_cache: dict[int, tuple[float, str]] = {}
_TTL = 20.0


def invalidate(tid: int):
    _cache.pop(tid, None)


def _piano_tenant(tid: int) -> str:
    hit = _cache.get(tid)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    db = SessionLocal()
    try:
        with tenancy.system_context():
            t = db.query(Tenant).filter(Tenant.id == tid).first()
        piano = (t.piano if t else "free") or "free"
    finally:
        db.close()
    _cache[tid] = (time.time(), piano)
    return piano


def _tenant_from_user(uid: int) -> int:
    from ..models import User
    db = SessionLocal()
    try:
        with tenancy.system_context():
            u = db.query(User).filter(User.id == uid).first()
            return (getattr(u, "tenant_id", None) or PLATFORM_TENANT_ID) if u else PLATFORM_TENANT_ID
    finally:
        db.close()


_IOT_RE = re.compile(r"^/api/iot/[a-z]+/(\d+)$")


def _iot_tenant(request: Request):
    """Per i webhook IoT (senza sessione) ricava il tenant dalla cotta e verifica il token del tenant."""
    m = _IOT_RE.match(request.url.path)
    if not m:
        return None, None
    from ..models import Cotta
    db = SessionLocal()
    try:
        with tenancy.system_context():
            c = db.query(Cotta).filter(Cotta.id == int(m.group(1))).first()
            if not c:
                return None, None
            tid = getattr(c, "tenant_id", None) or PLATFORM_TENANT_ID
            t = db.query(Tenant).filter(Tenant.id == tid).first()
            return tid, (t.iot_token if t else None)
    finally:
        db.close()


def _paywall(request: Request, richiesto: str):
    if request.url.path.startswith("/api/") or "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"error": "piano_insufficiente", "richiesto": richiesto,
                             "upgrade_url": f"/abbonamento?richiesto={richiesto}"}, status_code=402)
    return RedirectResponse(f"/abbonamento?richiesto={richiesto}", status_code=303)


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        ctx = None
        uid = request.session.get("user_id") if "session" in request.scope else None

        if uid:
            tid = request.session.get("tenant_id")
            if not tid:
                tid = _tenant_from_user(uid)
                request.session["tenant_id"] = tid
            ctx = TenantCtx(id=int(tid), piano=_piano_tenant(int(tid)))
        elif path.startswith("/api/iot/"):
            if request.method == "GET":
                return JSONResponse({"error": "Autenticazione richiesta"}, status_code=401)
            tid, token = _iot_tenant(request)
            if tid is None:
                return JSONResponse({"error": "Cotta non trovata"}, status_code=404)
            if tid != PLATFORM_TENANT_ID:
                provided = (request.query_params.get("token") or request.headers.get("x-api-key")
                            or request.headers.get("authorization", "").replace("Bearer ", "").strip() or "")
                if not token or not hmac.compare_digest(token, provided):
                    return JSONResponse({"error": "Token IoT non valido o mancante"}, status_code=401)
            ctx = TenantCtx(id=tid, piano=_piano_tenant(tid))
        elif path.startswith("/birre"):
            ctx = TenantCtx(id=PLATFORM_TENANT_ID, piano="b2b")

        if ctx is not None and uid:
            if not ctx.is_platform and any(path.startswith(p) for p in PLATFORM_ONLY):
                return RedirectResponse("/?msg=Funzione+non+disponibile", status_code=303)
            if ctx.livello < 2 and any(path.startswith(p) for p in B2B_ONLY):
                return _paywall(request, "b2b")

        token = tenancy.set_current(ctx)
        try:
            return await call_next(request)
        finally:
            tenancy.reset_current(token)
