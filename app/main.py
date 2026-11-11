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
from .routers import prodotti_finiti, costi_fissi, export_db, api_inventario, api_notifiche, dashboard, iot, procedure

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
        ("catalogo_ingredienti", "fermentable_type", "TEXT"),
        ("catalogo_ingredienti", "yield_percent", "REAL"),
        ("catalogo_ingredienti", "color_srm", "REAL"),
        ("catalogo_ingredienti", "alpha_acid", "REAL"),
        ("catalogo_ingredienti", "hop_use", "TEXT"),
        ("catalogo_ingredienti", "hop_form", "TEXT"),
        ("catalogo_ingredienti", "attenuation", "REAL"),
        ("catalogo_ingredienti", "yeast_type", "TEXT"),
        ("catalogo_ingredienti", "yeast_form", "TEXT"),
        ("catalogo_ingredienti", "misc_type", "TEXT"),
        ("catalogo_ingredienti", "misc_use", "TEXT"),
        ("ricette", "profilo_birrificio_id", "INTEGER"),
        ("ricette", "profilo_fermentazione_json", "TEXT"),
        ("profilo_birrificio", "boil_off_litri_ora", "REAL DEFAULT 2.5"),
        ("profilo_birrificio", "trub_loss_litri", "REAL DEFAULT 1.5"),
        ("profilo_birrificio", "mash_tun_deadspace_litri", "REAL DEFAULT 1.0"),
        ("profilo_birrificio", "assorbimento_grani_l_kg", "REAL DEFAULT 0.96"),
        ("profilo_birrificio", "rapporto_mash_l_kg", "REAL DEFAULT 3.0"),
        ("profilo_birrificio", "contrazione_termica_pct", "REAL DEFAULT 4.0"),
        ("catalogo_ingredienti", "codice", "TEXT"),
        ("inventario", "codice", "TEXT"),
        ("inventario", "codice_ingrediente", "TEXT"),
        ("ricette", "codice", "TEXT"),
        ("ingredienti_ricetta", "codice_ingrediente", "TEXT"),
        ("prodotti_finiti", "codice", "TEXT"),
        ("cotte", "checklist_json", "TEXT DEFAULT '{}'"),
    ]

    with engine.connect() as conn:
        # Tabelle aggiuntive create se non esistono
        # Usa sintassi compatibile con SQLite e PostgreSQL
        is_pg = engine.dialect.name == "postgresql"
        pk_type = "SERIAL PRIMARY KEY" if is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        extra_tables = [
            ("catalogo_ingredienti",
             f"id {pk_type}, nome TEXT NOT NULL, categoria TEXT NOT NULL, "
             "fermentable_type TEXT, yield_percent REAL, color_srm REAL, "
             "alpha_acid REAL, hop_use TEXT, hop_form TEXT, attenuation REAL, "
             "yeast_type TEXT, yeast_form TEXT, misc_type TEXT, misc_use TEXT"),
            ("prodotti_finiti",
             f"id {pk_type}, cotta_id INTEGER REFERENCES cotte(id), codice TEXT, "
             "nome TEXT NOT NULL, codice_lotto TEXT, formato_ml INTEGER DEFAULT 750, "
             "tipo_packaging TEXT DEFAULT 'bottiglia', n_pezzi_iniziali INTEGER DEFAULT 0, "
             "n_pezzi_disponibili INTEGER DEFAULT 0, data_imbottigliamento TEXT, "
             "data_scadenza TEXT, prezzo_vendita REAL, note TEXT, "
             "stato TEXT DEFAULT 'disponibile', created_at TEXT"),
            ("costi_fissi",
             f"id {pk_type}, categoria TEXT NOT NULL, descrizione TEXT NOT NULL, "
             "importo REAL DEFAULT 0, periodicita TEXT DEFAULT 'mensile', "
             "attivo INTEGER DEFAULT 1, note TEXT"),
            ("nuovi_articoli_pending",
             f"id {pk_type}, ordine_id INTEGER, riga_id INTEGER, "
             "nome TEXT, categoria TEXT, unita TEXT, quantita REAL, "
             "prezzo_unitario REAL, note TEXT"),
            ("prezzi_cache",
             f"id {pk_type}, query TEXT NOT NULL, fornitore TEXT NOT NULL, "
             "nome_prodotto TEXT NOT NULL, prezzo REAL, url TEXT, aggiornato_il TEXT"),
            ("cotta_ingredienti_lotti",
             f"id {pk_type}, cotta_id INTEGER REFERENCES cotte(id) NOT NULL, "
             "inventario_id INTEGER, codice_ingrediente TEXT, "
             "nome_ingrediente TEXT NOT NULL, categoria TEXT, numero_lotto TEXT, "
             "fornitore TEXT, data_scadenza TEXT, quantita_usata REAL DEFAULT 0.0, "
             "unita TEXT DEFAULT 'kg', timestamp TEXT, note TEXT"),
            ("procedure_operative",
             f"id {pk_type}, codice TEXT NOT NULL, titolo TEXT NOT NULL, "
             "fase TEXT DEFAULT 'brewday', revisione TEXT DEFAULT 'Rev. 1.0', "
             "scopo TEXT, dpi_attrezzature TEXT, parametri_critici TEXT, "
             "steps_json TEXT DEFAULT '[]', attiva INTEGER DEFAULT 1, updated_at TEXT"),
        ]
        for tname, tcols in extra_tables:
            if not table_exists(tname):
                try:
                    conn.execute(text(f"CREATE TABLE {tname} ({tcols})"))
                    conn.commit()
                except Exception:
                    conn.rollback()

        for table, col, col_type in alterations:
            if table_exists(table) and not column_exists(table, col):
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                    conn.commit()
                except Exception:
                    conn.rollback()

        # Sicurezza Supabase / PostgreSQL: abilita Row-Level Security (RLS) su tutte le tabelle
        # dello schema public e revoca l'accesso alle API pubbliche (anon, authenticated).
        # Non altera né elimina alcun dato; il backend FastAPI (ruolo proprietario/postgres)
        # mantiene accesso completo.
        if is_pg:
            try:
                rows = conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).fetchall()
                for (tname,) in rows:
                    safe_tname = tname.replace('"', '""')
                    try:
                        conn.execute(text(f'ALTER TABLE public."{safe_tname}" ENABLE ROW LEVEL SECURITY'))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                    try:
                        conn.execute(text(f'REVOKE ALL ON TABLE public."{safe_tname}" FROM anon, authenticated'))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                    try:
                        conn.execute(text(
                            f'DROP POLICY IF EXISTS "backend_full_access" ON public."{safe_tname}"; '
                            f'CREATE POLICY "backend_full_access" ON public."{safe_tname}" '
                            f'FOR ALL TO CURRENT_USER USING (true) WITH CHECK (true)'
                        ))
                        conn.commit()
                    except Exception:
                        conn.rollback()
            except Exception:
                conn.rollback()




run_migrations()


def auto_seed_data():
    """Auto-popola dati essenziali mancanti (catalogo 260 materie prime) senza sovrascrivere o alterare dati esistenti."""
    try:
        from .db import SessionLocal
        from .models import CatalogoIngrediente
        from .data_catalogo import TUTTO
        db = SessionLocal()
        try:
            n_cat = db.query(CatalogoIngrediente).count()
            if n_cat < 30:
                esistenti = { (i.nome or "").strip().lower() for i in db.query(CatalogoIngrediente.nome).all() }
                nuovi = [CatalogoIngrediente(**d) for d in TUTTO if (d.get("nome") or "").strip().lower() not in esistenti]
                if nuovi:
                    db.add_all(nuovi)
                    db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:
        pass


auto_seed_data()


def assegna_codici_retroattivi():
    """Assegna codici univoci standard (SKU, Ricetta, Cotta) a tutti i record privi di codice, preservando i dati esistenti."""
    try:
        from .db import SessionLocal
        from .models import CatalogoIngrediente, InventarioItem, Ricetta, Cotta, IngredienteRicetta, ProdottoFinito
        from .codici import prefisso_per_categoria
        import re

        db = SessionLocal()
        try:
            # Fast-check: se nessun record ha codice mancante, evita la scansione completa
            missing_any = (
                db.query(CatalogoIngrediente).filter((CatalogoIngrediente.codice == None) | (CatalogoIngrediente.codice == "")).first()
                or db.query(InventarioItem).filter((InventarioItem.codice == None) | (InventarioItem.codice == "")).first()
                or db.query(Ricetta).filter((Ricetta.codice == None) | (Ricetta.codice == "")).first()
                or db.query(Cotta).filter((Cotta.codice == None) | (Cotta.codice == "")).first()
                or db.query(ProdottoFinito).filter((ProdottoFinito.codice == None) | (ProdottoFinito.codice == "")).first()
            )
            if not missing_any:
                return

            # 1. CATALOGO INGREDIENTI (Assegna SKU: MAL-001, LUP-001, LIE-001, MIS-001, CHI-001, PAC-001)
            all_cat = db.query(CatalogoIngrediente).order_by(CatalogoIngrediente.id.asc()).all()
            conteggi = {"MAL": 0, "LUP": 0, "LIE": 0, "MIS": 0, "CHI": 0, "PAC": 0}
            pattern = re.compile(r"^([A-Z]+)-(\d+)$")

            for item in all_cat:
                if item.codice:
                    m = pattern.match(item.codice.strip())
                    if m and m.group(1) in conteggi:
                        conteggi[m.group(1)] = max(conteggi[m.group(1)], int(m.group(2)))

            sku_per_nome = {}
            for item in all_cat:
                if not item.codice:
                    pref = prefisso_per_categoria(item.categoria)
                    conteggi[pref] += 1
                    item.codice = f"{pref}-{conteggi[pref]:03d}"
                sku_per_nome[(item.nome or "").strip().lower()] = item.codice

            # 2. INVENTARIO ITEM (Sincronizza codice_ingrediente ed assegna codice articolo)
            all_inv = db.query(InventarioItem).all()
            for inv in all_inv:
                clean_name = (inv.nome or "").strip().lower()
                sku = sku_per_nome.get(clean_name)
                if not sku:
                    for k, v in sku_per_nome.items():
                        if k in clean_name or clean_name in k:
                            sku = v
                            break
                if not inv.codice_ingrediente:
                    inv.codice_ingrediente = sku or f"INV-{inv.id:03d}"
                if not inv.codice:
                    inv.codice = inv.codice_ingrediente

            # 3. RICETTE (Assegna RIC-001, RIC-002...)
            all_ric = db.query(Ricetta).order_by(Ricetta.id.asc()).all()
            ric_max = 0
            for r in all_ric:
                if r.codice:
                    m = re.match(r"^RIC-(\d+)$", r.codice.strip())
                    if m:
                        ric_max = max(ric_max, int(m.group(1)))
            for r in all_ric:
                if not r.codice:
                    ric_max += 1
                    r.codice = f"RIC-{ric_max:03d}"

            # 4. INGREDIENTI RICETTA (Collega codice_ingrediente SKU)
            all_ing_ric = db.query(IngredienteRicetta).all()
            for ing in all_ing_ric:
                if not ing.codice_ingrediente:
                    cname = (ing.nome or "").strip().lower()
                    sku = sku_per_nome.get(cname)
                    if not sku:
                        for k, v in sku_per_nome.items():
                            if k in cname or cname in k:
                                sku = v
                                break
                    ing.codice_ingrediente = sku

            # 5. COTTE (Assegna COT-YYYY-NNN)
            all_cotte = db.query(Cotta).order_by(Cotta.id.asc()).all()
            cotte_per_anno = {}
            for c in all_cotte:
                if c.codice:
                    m = re.match(r"^COT-(\d{4})-(\d+)$", c.codice.strip())
                    if m:
                        y = m.group(1)
                        num = int(m.group(2))
                        cotte_per_anno[y] = max(cotte_per_anno.get(y, 0), num)

            for c in all_cotte:
                if not c.codice:
                    anno = "2026"
                    if c.data_brew and len(c.data_brew) >= 4 and c.data_brew[:4].isdigit():
                        anno = c.data_brew[:4]
                    cotte_per_anno[anno] = cotte_per_anno.get(anno, 0) + 1
                    c.codice = f"COT-{anno}-{cotte_per_anno[anno]:03d}"

            # 6. PRODOTTI FINITI (Assegna SKU PF-NNN e assicura codice_lotto standard)
            all_pf = db.query(ProdottoFinito).order_by(ProdottoFinito.id.asc()).all()
            pf_max = 0
            for pf in all_pf:
                if pf.codice:
                    m = re.match(r"^PF-(\d+)$", pf.codice.strip())
                    if m:
                        pf_max = max(pf_max, int(m.group(1)))

            for pf in all_pf:
                if not pf.codice:
                    pf_max += 1
                    pf.codice = f"PF-{pf_max:03d}"
                if not pf.codice_lotto:
                    cotta_code = pf.cotta.codice if (pf.cotta and pf.cotta.codice) else (f"COT-2026-{pf.cotta_id:03d}" if pf.cotta_id else "LOTTO")
                    fmt = pf.formato_ml or 330
                    pf.codice_lotto = f"L-{cotta_code}-{fmt}ML"

            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
    except Exception:
        pass


assegna_codici_retroattivi()

# ── AUTH MIDDLEWARE ───────────────────────────────────────────────────────────

EXEMPT = ("/login", "/register", "/birre", "/debug/version", "/api/iot", "/static", "/recupera-password")
READ_ONLY_PATHS = ("/", "/ricette/html", "/ricette/libreria", "/cotte", "/stili", "/catalogo",
                   "/strumenti", "/profili-acqua", "/prezzi", "/impianto",
                   "/tracciabilita", "/inventario", "/procedure")

WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")
# Scritture consentite anche per utenti non-soci (solo queste route)
SOCIO_EXEMPT_WRITES = ("/diventa-socio", "/ricette/libreria/importa", "/catalogo/ingredienti/popola_completo", "/catalogo/ingredienti/popola_demo")


def _add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(e) for e in EXEMPT):
            response = await call_next(request)
            return _add_security_headers(response)
        user_id = request.session.get("user_id")
        if not user_id and user_id != 0:
            return _add_security_headers(RedirectResponse("/login", status_code=303))
        ruolo = request.session.get("ruolo", "birraio")
        # Ospite e birraio (non-socio): blocca azioni di scrittura
        if ruolo in ("ospite", "birraio") and request.method in WRITE_METHODS:
            if any(path.startswith(e) for e in SOCIO_EXEMPT_WRITES):
                response = await call_next(request)
                return _add_security_headers(response)
            if ruolo == "ospite":
                msg = "Sei in modalità ospite (sola lettura).<br>Esegui il login per modificare i dati."
                cta = '<a href="/login" style="display:inline-block;margin-top:12px;padding:10px 20px;background:#f59e0b;color:#000;border-radius:8px;text-decoration:none;font-weight:700;">Accedi</a>'
            else:
                msg = "Solo i soci possono registrare dati operativi.<br>Diventa socio per sbloccare tutte le funzionalità."
                cta = '<a href="/diventa-socio" style="display:inline-block;margin-top:12px;padding:10px 20px;background:#f59e0b;color:#000;border-radius:8px;text-decoration:none;font-weight:700;">✦ Diventa Socio</a>'
            return _add_security_headers(HTMLResponse(
                '<html><body style="background:#0d1117;color:#e6edf3;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;">'
                f'<div><div style="font-size:48px;">🔒</div><h2>Accesso negato</h2>'
                f'<p style="color:#8b949e;">{msg}</p>{cta}'
                '<br><br><a href="/" style="color:#8b949e;font-size:13px;">← Torna alla home</a></div></body></html>',
                status_code=403
            ))
        response = await call_next(request)
        return _add_security_headers(response)


# ── APP ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Gestionale Birrificio")
app.add_middleware(AuthMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    max_age=86400 * 14,
    https_only=bool(os.environ.get("RENDER") or os.environ.get("DATABASE_URL")),
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    err_tb = traceback.format_exc()
    print(f"CRITICAL ERROR on {request.method} {request.url.path}: {err_tb}", flush=True)
    is_admin = False
    try:
        is_admin = request.session.get("ruolo") == "admin"
    except Exception:
        pass
    tech_details = ""
    if is_admin:
        tech_details = f"""
  <p><strong>Dettaglio:</strong> {exc}</p>
  <details open style="margin-top:16px;">
    <summary style="cursor:pointer; color:#58a6ff; margin-bottom:8px; font-weight:600;">Dettagli tecnici traceback (visibili solo all'Admin)</summary>
    <pre>{err_tb}</pre>
  </details>"""
    else:
        tech_details = "<p style='color:#8b949e;'>L'errore tecnico è stato registrato nei log del server. Se il problema persiste, contatta l'amministratore.</p>"
    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Errore 500 - Gestionale Birrificio</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif; background: #0d1117; color: #e6edf3; padding: 24px; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 24px; max-width: 800px; margin: 30px auto; }}
h2 {{ color: #f85149; margin-top: 0; }}
pre {{ background: #0d1117; padding: 14px; border-radius: 6px; overflow-x: auto; color: #f87171; font-size: 13px; border: 1px solid #30363d; line-height: 1.4; }}
a {{ color: #58a6ff; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="card">
  <h2>⚠️ Si è verificato un errore sul server (500)</h2>
  <p><strong>Percorso:</strong> {request.url.path}</p>{tech_details}
  <div style="margin-top:20px;">
    <a href="/">← Torna alla Home</a> &nbsp;|&nbsp;
    <a href="javascript:history.back()">← Torna Indietro</a>
  </div>
</div>
</body>
</html>""",
        status_code=500
    )


@app.get("/debug/version")
def debug_version():
    return {
        "status": "online",
        "app": "Gestionale Birrificio",
        "build": "2026-11-01_1330_filiera_completa_prodotti_finiti",
    }


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
app.include_router(api_notifiche.router)
app.include_router(dashboard.router)
app.include_router(iot.router)
app.include_router(procedure.router)

@app.get("/amministrazione", response_class=HTMLResponse)
def amministrazione(request: Request):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
        
    from .db import SessionLocal
    from .models import Impostazioni
    db = SessionLocal()
    ultimo_backup = "Mai effettuato"
    try:
        imp = db.query(Impostazioni).filter(Impostazioni.chiave == "ultimo_backup").first()
        if imp and imp.valore:
            ultimo_backup = imp.valore
    except Exception:
        pass
    finally:
        db.close()
        
    return templates.TemplateResponse(request, "amministrazione.html", {
        "session": request.session,
        "ultimo_backup": ultimo_backup
    })


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {
        "session": request.session,
    })


@app.get("/debug/seed-admin")
def seed_admin(request: Request):
    from .db import SessionLocal
    from .models import User
    db = SessionLocal()
    try:
        if db.query(User).count() > 0 and request.session.get("ruolo") != "admin":
            return HTMLResponse("Accesso riservato agli amministratori.", status_code=403)
        u = db.query(User).filter(User.username == "admin").first()
        if not u:
            u = User(username="admin", password_hash=User.hash_pw("admin123"),
                     nome="Amministratore", ruolo="admin")
            db.add(u)
            db.commit()
            return {"created": True, "username": "admin"}
        return {"exists": True, "username": "admin"}
    finally:
        db.close()


@app.get("/api/stats-home")
def stats_home():
    from .db import SessionLocal
    from .models import Ricetta, Cotta, CatalogoIngrediente, Stile, Degustazione, STATI_COTTA
    db = SessionLocal()
    try:
        FASI_DETT = {
            "pianificata": {"label": "Pianificata", "color": "#64748b", "bg": "rgba(100,116,139,0.15)", "pct": 10},
            "brewday": {"label": "Brew Day (Cotta)", "color": "#f59e0b", "bg": "rgba(245,158,11,0.15)", "pct": 25},
            "fermentazione": {"label": "Fermentazione Primaria", "color": "#10b981", "bg": "rgba(16,185,129,0.15)", "pct": 50},
            "secondaria": {"label": "Fermentazione Secondaria / Dry Hop", "color": "#06b6d4", "bg": "rgba(6,182,212,0.15)", "pct": 70},
            "condizionamento": {"label": "Condizionamento / Lagering", "color": "#3b82f6", "bg": "rgba(59,130,246,0.15)", "pct": 80},
            "imbottigliamento": {"label": "Imbottigliamento / Fusto", "color": "#8b5cf6", "bg": "rgba(139,92,246,0.15)", "pct": 90},
            "maturazione": {"label": "Maturazione in Bottiglia", "color": "#ec4899", "bg": "rgba(236,72,153,0.15)", "pct": 95},
            "pronta": {"label": "Pronta per la Spina", "color": "#10b981", "bg": "rgba(16,185,129,0.2)", "pct": 100},
        }

        cotte_attive = (
            db.query(Cotta)
            .filter(Cotta.stato.notin_(["archiviata"]))
            .order_by(Cotta.id.desc())
            .all()
        )

        cotte_out = []
        tot_litri_in_prod = 0.0
        for c in cotte_attive:
            finfo = FASI_DETT.get(c.stato, {"label": c.stato.capitalize(), "color": "#f59e0b", "bg": "rgba(245,158,11,0.15)", "pct": 50})
            litri = float(c.volume_imbottigliato or c.volume_post_bollitura or (c.ricetta.volume_target_litri if c.ricetta else 20.0) or 20.0)
            if c.stato != "pronta":
                tot_litri_in_prod += litri

            cotte_out.append({
                "id": c.id,
                "nome": c.nome,
                "codice": c.codice or f"COT-{c.id:03d}",
                "stato": c.stato,
                "fase_label": finfo["label"],
                "fase_colore": "amber" if finfo["pct"] <= 25 else ("green" if finfo["pct"] <= 60 else ("blue" if finfo["pct"] <= 85 else "purple")),
                "fase_progresso": finfo["pct"],
                "color": finfo["color"],
                "bg": finfo["bg"],
                "pct": finfo["pct"],
                "ricetta": c.ricetta.nome if c.ricetta else "Ricetta personalizzata",
                "stile": c.ricetta.stile.nome if (c.ricetta and c.ricetta.stile) else "Stile libero",
                "data_brew": c.data_brew or "—",
                "data_cotta": c.data_brew or "—",
                "fermentatore": c.fermentatore or "Non assegnato",
                "temp": f"{c.temp_fermentazione}°C" if c.temp_fermentazione else "N/D",
                "og": c.og_reale or (c.ricetta.og if c.ricetta else None),
                "fg": c.fg_reale or (c.ricetta.fg if c.ricetta else None),
                "litri": round(litri, 1),
            })

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
            "n_cotte": len([c for c in cotte_attive if c.stato != "pronta"]),
            "tot_litri_produzione": round(tot_litri_in_prod, 1),
            "n_catalogo": db.query(CatalogoIngrediente).count(),
            "n_stili": db.query(Stile).count(),
            "cotte_attive": cotte_out,
            "produzione_dettaglio": cotte_out,
            "degustazioni": degu_out,
        }
    finally:
        db.close()


@app.get("/debug/reset-admin")
def reset_admin(request: Request):
    if request.session.get("ruolo") != "admin":
        return HTMLResponse("Accesso negato: riservato agli amministratori autenticati.", status_code=403)
    from .db import SessionLocal
    from .models import User
    db = SessionLocal()
    try:
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
        return {"reset": True, "username": "admin"}
    finally:
        db.close()
