"""Export e Import del database (compatibile con SQLite e PostgreSQL)."""
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, date

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTask
from sqlalchemy import inspect, text

from ..db import engine, SessionLocal
from ..models import Impostazioni

router = APIRouter()
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger("export_db")


def _aggiorna_ultimo_backup():
    """Aggiorna il timestamp dell'ultimo backup nel database."""
    db = SessionLocal()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        imp = db.query(Impostazioni).filter(Impostazioni.chiave == "ultimo_backup").first()
        if not imp:
            imp = Impostazioni(chiave="ultimo_backup", valore=now_str)
            db.add(imp)
        else:
            imp.valore = now_str
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Impossibile aggiornare timestamp ultimo_backup: {e}")
    finally:
        db.close()


def genera_backup_sqlite() -> str:
    """
    Genera un file SQLite di backup valido e consistente.
    Se l'applicazione usa SQLite, esegue un backup online senza lock.
    Se l'applicazione usa PostgreSQL (Supabase/Render), effettua il dump di tutte le tabelle in un file SQLite.
    Restituisce il path del file temporaneo creato.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_path = tmp.name
    tmp.close()

    is_sqlite = engine.url.drivername.startswith("sqlite")

    if is_sqlite:
        db_file = engine.url.database or ""
        candidati = [
            db_file,
            "./gestionale_birra.db",
            "gestionale_birra.db",
            "./birrificio.db",
            "birrificio.db",
        ]
        source_path = None
        for c in candidati:
            if c and os.path.exists(c) and os.path.isfile(c) and os.path.getsize(c) > 0:
                source_path = c
                break

        if source_path:
            try:
                src_conn = sqlite3.connect(source_path)
                dst_conn = sqlite3.connect(tmp_path)
                src_conn.backup(dst_conn)
                src_conn.close()
                dst_conn.close()
                return tmp_path
            except Exception as e:
                logger.warning(f"Errore backup diretto SQLite da {source_path}: {e}")

    # Dump universale da SQLAlchemy (per PostgreSQL o se il file SQLite locale non è leggibile)
    sqlite_conn = sqlite3.connect(tmp_path)
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    with engine.connect() as conn:
        for t_name in table_names:
            try:
                cols = inspector.get_columns(t_name)
                if not cols:
                    continue
                col_defs = []
                for c in cols:
                    col_name = c["name"]
                    c_type = str(c.get("type", "")).lower()
                    sql_type = "TEXT"
                    if "int" in c_type:
                        sql_type = "INTEGER"
                    elif any(x in c_type for x in ("float", "real", "numeric", "decimal")):
                        sql_type = "REAL"
                    col_defs.append(f'"{col_name}" {sql_type}')

                create_stmt = f'CREATE TABLE IF NOT EXISTS "{t_name}" ({", ".join(col_defs)})'
                sqlite_conn.execute(create_stmt)

                res = conn.execute(text(f'SELECT * FROM "{t_name}"')).fetchall()
                if res:
                    placeholders = ", ".join(["?"] * len(cols))
                    col_names = ", ".join(f'"{c["name"]}"' for c in cols)
                    insert_stmt = f'INSERT INTO "{t_name}" ({col_names}) VALUES ({placeholders})'

                    rows_to_insert = []
                    for row in res:
                        row_vals = []
                        for v in row:
                            if isinstance(v, bool):
                                row_vals.append(1 if v else 0)
                            elif isinstance(v, (datetime, date)):
                                row_vals.append(v.isoformat())
                            else:
                                row_vals.append(v)
                        rows_to_insert.append(tuple(row_vals))

                    sqlite_conn.executemany(insert_stmt, rows_to_insert)
                sqlite_conn.commit()
            except Exception as e:
                logger.warning(f"Errore esportazione tabella {t_name}: {e}")
                continue

    sqlite_conn.close()
    return tmp_path


def genera_backup_json() -> str:
    """
    Genera un dump JSON completo di tutte le tabelle per backup testuale e ispezione.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
    tmp_path = tmp.name

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    data = {
        "export_timestamp": datetime.now().isoformat(),
        "tables": {}
    }

    with engine.connect() as conn:
        for t_name in table_names:
            try:
                res = conn.execute(text(f'SELECT * FROM "{t_name}"'))
                cols = [c["name"] for c in inspector.get_columns(t_name)]
                rows = []
                for r in res.fetchall():
                    row_dict = {}
                    for col_name, val in zip(cols, r):
                        if isinstance(val, (datetime, date)):
                            row_dict[col_name] = val.isoformat()
                        elif isinstance(val, bytes):
                            row_dict[col_name] = "<binary data>"
                        else:
                            row_dict[col_name] = val
                    rows.append(row_dict)
                data["tables"][t_name] = rows
            except Exception as e:
                logger.warning(f"Errore dump JSON tabella {t_name}: {e}")
                continue

    json.dump(data, tmp, indent=2, ensure_ascii=False)
    tmp.close()
    return tmp_path


@router.get("/admin/export-db")
def export_db(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"gestionale_birra_{ts}.db"

    _aggiorna_ultimo_backup()

    try:
        tmp_path = genera_backup_sqlite()
        return FileResponse(
            tmp_path,
            media_type="application/octet-stream",
            filename=fname,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            background=BackgroundTask(lambda: os.path.exists(tmp_path) and os.remove(tmp_path)),
        )
    except Exception as e:
        logger.error(f"Errore durante esportazione database: {e}")
        return HTMLResponse(f"Errore durante l'esportazione del backup: {e}", status_code=500)


@router.get("/admin/export-json")
def export_json(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"gestionale_birra_{ts}.json"

    _aggiorna_ultimo_backup()

    try:
        tmp_path = genera_backup_json()
        return FileResponse(
            tmp_path,
            media_type="application/json",
            filename=fname,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            background=BackgroundTask(lambda: os.path.exists(tmp_path) and os.remove(tmp_path)),
        )
    except Exception as e:
        logger.error(f"Errore durante esportazione JSON: {e}")
        return HTMLResponse(f"Errore durante l'esportazione del backup JSON: {e}", status_code=500)


@router.post("/admin/import-db")
async def import_db(request: Request, file: UploadFile = File(...)):
    ruolo = request.session.get("ruolo", "")
    if ruolo != "admin":
        return HTMLResponse("Accesso negato: il ripristino è riservato agli amministratori", status_code=403)

    data = await file.read()
    if len(data) < 100:
        return HTMLResponse("File troppo piccolo o non valido", status_code=400)
    if not data[:16].startswith(b"SQLite format 3"):
        return HTMLResponse("File non è un database SQLite valido", status_code=400)

    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_in_path = tmp_in.name
    tmp_in.write(data)
    tmp_in.close()

    is_sqlite = engine.url.drivername.startswith("sqlite")
    try:
        if is_sqlite:
            db_path = engine.url.database or "./gestionale_birra.db"
            bak = db_path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            if os.path.exists(db_path):
                shutil.copy2(db_path, bak)
            with open(db_path, "wb") as f:
                f.write(data)
        else:
            # PostgreSQL / Supabase
            sqlite_conn = sqlite3.connect(tmp_in_path)
            sqlite_conn.row_factory = sqlite3.Row
            cursor = sqlite_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            uploaded_tables = [r[0] for r in cursor.fetchall()]

            inspector = inspect(engine)
            existing_tables = set(inspector.get_table_names())

            with engine.begin() as pg_conn:
                for t in uploaded_tables:
                    if t not in existing_tables:
                        continue
                    pragma = sqlite_conn.execute(f'PRAGMA table_info("{t}")').fetchall()
                    cols = [p[1] for p in pragma]
                    rows = sqlite_conn.execute(f'SELECT * FROM "{t}"').fetchall()

                    pg_conn.execute(text(f'DELETE FROM "{t}"'))
                    if rows:
                        col_names = ", ".join(f'"{c}"' for c in cols)
                        params_str = ", ".join(f':{c}' for c in cols)
                        stmt = text(f'INSERT INTO "{t}" ({col_names}) VALUES ({params_str})')
                        clean_data = [dict(r) for r in rows]
                        pg_conn.execute(stmt, clean_data)

            sqlite_conn.close()

        _aggiorna_ultimo_backup()

    except Exception as e:
        logger.error(f"Errore durante importazione database: {e}")
        return HTMLResponse(f"Errore durante l'importazione del database: {e}", status_code=500)
    finally:
        if os.path.exists(tmp_in_path):
            os.remove(tmp_in_path)

    return RedirectResponse("/amministrazione?msg=Database+ripristinato+con+successo", status_code=303)
