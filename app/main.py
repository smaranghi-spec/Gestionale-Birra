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
from .routers import prezzi, fattura, brewmonk, soci
from .routers import impianto, profili_acqua, costo_ricetta, tracciabilita
from .routers import strumenti, lista_acquisti, ai_assistant, aggiunte_cotta, importa_foto
from .routers import prodotti_finiti, costi_fissi, export_db, api_inventario

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")

SECRET_KEY = os.environ.get("SECRET_KEY", "birrificio-gestionale-2024-segreto")


def run_migrations():
    """Aggiunge colonne mancanti in modo sicuro, compatibile con SQLite e PostgreSQL."""
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(engine)

    def column_exists(table, col):
        try:
            cols = [c["name"] for c in inspector.get_columns(table)]
            return col in cols
        except Exception:
            return False

    def table_exists(table):
        return inspector.has_table(table)

    alterations = [
        ("ingredienti_ricetta", "prezzo_unitario", "REAL"),
        ("ricette", "pubblica", "INTEGER DEFAULT 0"),
        ("users", "nome", "TEXT DEFAULT ''"),
        ("users", "ruolo", "TEXT DEFAULT 'birraio'"),
        ("users", "reset_richiesto", "INTEGER DEFAULT 0"),
        ("inventario", "tipo_ingrediente", "TEXT"),
        ("inventario", "numero_lotto", "TEXT"),
        ("inventario", "data_scadenza", "TEXT"),
        ("inventario", "alfa_acidi", "REAL"),
        ("inventario", "ibu_teorici", "REAL"),
        ("inventario", "attenuazione", "REAL"),
        ("inventario", "flocculazione", "TEXT"),
        ("inventario", "resa_estratto", "REAL"),
        ("inventario", "colore_ebc", "REAL"),
        ("cotte", "temp_ambiente", "REAL"),
        ("cotte", "acqua_totale_litri", "REAL"),
        ("cotte", "pressione_bar", "REAL"),
        ("cotte", "note_ferm", "TEXT"),
        ("cotte", "note_cond", "TEXT"),
        ("cotte", "note_imbott", "TEXT"),
        ("ordini_acquisto", "acquirente", "TEXT"),
        ("ingredienti_ricetta", "numero_lotto", "TEXT"),
        ("ingredienti_ricetta", "fornitore_lotto", "TEXT"),
        ("ingredienti_ricetta", "data_scadenza_lotto", "TEXT"),
        ("vendite", "stato", "TEXT DEFAULT 'confermata'"),
        ("degustazioni", "limpidezza", "REAL"),
        ("degustazioni", "colore", "REAL"),
        ("degustazioni", "schiuma", "REAL"),
        ("degustazioni", "intensita_olfattiva", "REAL"),
        ("degustazioni", "finezza_olfattiva", "REAL"),
        ("degustazioni", "complessita_olfattiva", "REAL"),
        ("degustazioni", "corpo", "REAL"),
        ("degustazioni", "equilibrio", "REAL"),
        ("degustazioni", "persistenza_gusto_olfattiva", "REAL"),
        ("degustazioni", "impressione_generale", "REAL"),
    ]

    with engine.connect() as conn:
        for table, col, col_type in alterations:
            if table_exists(table) and not column_exists(table, col):
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
                except Exception:
                    conn.rollback()

        # Tabelle aggiuntive create se non esistono
        extra_tables = [
            ("prodotti_finiti",
             "id SERIAL PRIMARY KEY, cotta_id INTEGER REFERENCES cotte(id), "
             "nome TEXT NOT NULL, codice_lotto TEXT, formato_ml INTEGER DEFAULT 750, "
             "tipo_packaging TEXT DEFAULT 'bottiglia', n_pezzi_iniziali INTEGER DEFAULT 0, "
             "n_pezzi_disponibili INTEGER DEFAULT 0, data_imbottigliamento TEXT, "
             "data_scadenza TEXT, prezzo_vendita REAL, note TEXT, "
             "stato TEXT DEFAULT 'disponibile', created_at TEXT"),
            ("costi_fissi",
             "id SERIAL PRIMARY KEY, categoria TEXT NOT NULL, descrizione TEXT NOT NULL, "
             "importo REAL DEFAULT 0, periodicita TEXT DEFAULT 'mensile', "
             "attivo INTEGER DEFAULT 1, note TEXT"),
            ("nuovi_articoli_pending",
             "id SERIAL PRIMARY KEY, ordine_id INTEGER, riga_id INTEGER, "
             "nome TEXT, categoria TEXT, unita TEXT, quantita REAL, "
             "prezzo_unitario REAL, note TEXT"),
        ]
        for tname, tcols in extra_tables:
            if not table_exists(tname):
                try:
                    conn.execute(text(f"CREATE TABLE {tname} ({tcols})"))
                    conn.commit()
                except Exception:
                    conn.rollback()


run_migrations()

# ── AUTH MIDDLEWARE ───────────────────────────────────────────────────────────

EXEMPT = ("/login", "/register", "/birre", "/debug", "/static", "/recupera-password")
READ_ONLY_PATHS = ("/", "/ricette/html", "/cotte", "/stili", "/catalogo",
                   "/strumenti", "/profili-acqua", "/prezzi", "/impianto",
                   "/tracciabilita", "/inventario")

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
# Scritture consentite anche per utenti non-soci (solo queste route)
SOCIO_EXEMPT_WRITES = ("/diventa-socio",)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(e) for e in EXEMPT):
            return await call_next(request)
        user_id = request.session.get("user_id")
        if not user_id and user_id != 0:
            return RedirectResponse("/login", status_code=303)
        ruolo = request.session.get("ruolo", "birraio")
        # Ospite e birraio (non-socio): blocca azioni di scrittura
        if ruolo in ("ospite", "birraio") and request.method in WRITE_METHODS:
            if any(path.startswith(e) for e in SOCIO_EXEMPT_WRITES):
                return await call_next(request)
            if ruolo == "ospite":
                msg = "Sei in modalità ospite (sola lettura).<br>Esegui il login per modificare i dati."
                cta = '<a href="/login" style="display:inline-block;margin-top:12px;padding:10px 20px;background:#f59e0b;color:#000;border-radius:8px;text-decoration:none;font-weight:700;">Accedi</a>'
            else:
                msg = "Solo i soci possono registrare dati operativi.<br>Diventa socio per sbloccare tutte le funzionalità."
                cta = '<a href="/diventa-socio" style="display:inline-block;margin-top:12px;padding:10px 20px;background:#f59e0b;color:#000;border-radius:8px;text-decoration:none;font-weight:700;">✦ Diventa Socio</a>'
            return HTMLResponse(
                '<html><body style="background:#0d1117;color:#e6edf3;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;">'
                f'<div><div style="font-size:48px;">🔒</div><h2>Accesso negato</h2>'
                f'<p style="color:#8b949e;">{msg}</p>{cta}'
                '<br><br><a href="/" style="color:#8b949e;font-size:13px;">← Torna alla home</a></div></body></html>',
                status_code=403
            )
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
app.include_router(importa_foto.router)  # deve stare prima di acquisti (evita conflitto /{oid})
app.include_router(acquisti.router)
app.include_router(vendite.router)
app.include_router(attrezzature.router)
app.include_router(calendario.router)
app.include_router(pulizie.router)
app.include_router(inventario.router)
app.include_router(birre_pub.router)
app.include_router(prezzi.router)
app.include_router(fattura.router)
app.include_router(brewmonk.router)
app.include_router(soci.router)
app.include_router(impianto.router)
app.include_router(profili_acqua.router)
app.include_router(costo_ricetta.router)
app.include_router(tracciabilita.router)
app.include_router(strumenti.router)
app.include_router(lista_acquisti.router)
app.include_router(ai_assistant.router)
app.include_router(aggiunte_cotta.router)
app.include_router(prodotti_finiti.router)
app.include_router(costi_fissi.router)
app.include_router(export_db.router)
app.include_router(api_inventario.router)


@app.get("/amministrazione", response_class=HTMLResponse)
def amministrazione(request: Request):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "amministrazione.html", {
        "session": request.session,
    })


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
    from .models import Ricetta, Cotta, CatalogoIngrediente, Stile, Degustazione
    db = SessionLocal()
    try:
        cotte_attive = db.query(Cotta).filter(
            Cotta.stato.notin_(["archiviata", "pronta"])
        ).order_by(Cotta.id.desc()).limit(5).all()

        degs = db.query(Degustazione).order_by(Degustazione.id.desc()).limit(6).all()
        degu_out = []
        for d in degs:
            cotta = db.query(Cotta).filter(Cotta.id == d.cotta_id).first()
            punteggio = None
            if any([d.aroma, d.gusto, d.aspetto, d.sensazione]):
                vals = [v for v in [d.aroma, d.gusto, d.aspetto, d.sensazione] if v]
                punteggio = round(sum(vals) / len(vals), 1) if vals else None
            degu_out.append({
                "cotta": cotta.nome if cotta else "—",
                "degustatore": d.degustatore,
                "data": d.data,
                "voto": f"{punteggio}/10" if punteggio else None,
            })

        return {
            "n_ricette": db.query(Ricetta).count(),
            "n_cotte": db.query(Cotta).filter(Cotta.stato != "archiviata").count(),
            "n_catalogo": db.query(CatalogoIngrediente).count(),
            "n_stili": db.query(Stile).count(),
            "cotte_attive": [{"id": c.id, "nome": c.nome, "stato": c.stato, "ricetta": c.ricetta.nome if c.ricetta else ""} for c in cotte_attive],
            "degustazioni": degu_out,
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
