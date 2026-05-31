import os
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .db import engine
from .models import Base
from .routers import (
    ricette, catalogo, ingredienti, stili, cotte, importa,
    acquisti, vendite, auth_router,
)
from .routers import attrezzature, calendario, pulizie, inventario, birre_pub
from .routers import prezzi, fattura

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.environ.get("SECRET_KEY", "birrificio-gestionale-2024-segreto")


def run_migrations():
    import sqlite3
    conn = sqlite3.connect("./gestionale_birra.db")
    for sql in [
        "ALTER TABLE ingredienti_ricetta ADD COLUMN prezzo_unitario REAL",
        "ALTER TABLE ricette ADD COLUMN pubblica INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN nome TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN ruolo TEXT DEFAULT 'birraio'",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


run_migrations()

# ── AUTH MIDDLEWARE ───────────────────────────────────────────────────────────

EXEMPT = ("/login", "/register", "/birre", "/debug", "/static")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(e) for e in EXEMPT):
            return await call_next(request)
        user_id = request.session.get("user_id")
        if not user_id:
            return RedirectResponse("/login", status_code=303)
        return await call_next(request)


# ── APP ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Gestionale Birrificio")
app.add_middleware(AuthMiddleware)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(auth_router.router)
app.include_router(ricette.router)
app.include_router(catalogo.router)
app.include_router(ingredienti.router)
app.include_router(stili.router)
app.include_router(cotte.router)
app.include_router(importa.router)
app.include_router(acquisti.router)
app.include_router(vendite.router)
app.include_router(attrezzature.router)
app.include_router(calendario.router)
app.include_router(pulizie.router)
app.include_router(inventario.router)
app.include_router(birre_pub.router)
app.include_router(prezzi.router)
app.include_router(fattura.router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {
        "session": request.session,
    })


@app.get("/debug/seed-admin")
def seed_admin():
    from .db import SessionLocal
    from .models import User
    db = SessionLocal()
    u = db.query(User).filter(User.username == "admin").first()
    if not u:
        u = User(username="admin", password_hash=User.hash_pw("admin123"),
                 nome="Amministratore", ruolo="admin")
        db.add(u)
        db.commit()
        db.close()
        return {"created": True, "username": "admin", "password": "admin123"}
    db.close()
    return {"exists": True, "username": "admin",
            "hint": "Se non riesci ad accedere vai a /debug/reset-admin"}


@app.get("/api/stats-home")
def stats_home():
    from .db import SessionLocal
    from .models import Ricetta, Cotta, CatalogoIngrediente, Stile
    db = SessionLocal()
    try:
        return {
            "n_ricette": db.query(Ricetta).count(),
            "n_cotte": db.query(Cotta).filter(Cotta.stato != "archiviata").count(),
            "n_catalogo": db.query(CatalogoIngrediente).count(),
            "n_stili": db.query(Stile).count(),
        }
    finally:
        db.close()


@app.get("/debug/reset-admin")
def reset_admin():
    from .db import SessionLocal
    from .models import User
    db = SessionLocal()
    u = db.query(User).filter(User.username == "admin").first()
    if u:
        u.password_hash = User.hash_pw("admin123")
        u.ruolo = "admin"
        u.is_active = True
    else:
        u = User(username="admin", password_hash=User.hash_pw("admin123"),
                 nome="Amministratore", ruolo="admin")
        db.add(u)
    db.commit()
    db.close()
    return {"reset": True, "username": "admin", "password": "admin123"}
