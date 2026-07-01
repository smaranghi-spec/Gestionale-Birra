"""Export e Import del database SQLite."""
import os
import shutil
import tempfile
from datetime import datetime

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DB_PATH = "./gestionale_birra.db"


@router.get("/admin/export-db")
def export_db(request: Request):
    ruolo = request.session.get("ruolo", "")
    if ruolo != "admin":
        return HTMLResponse("Accesso negato", status_code=403)
    if not os.path.exists(DB_PATH):
        return HTMLResponse("Database non trovato", status_code=404)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"gestionale_birra_{ts}.db"
    return FileResponse(
        DB_PATH,
        media_type="application/octet-stream",
        filename=fname,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.post("/admin/import-db")
async def import_db(request: Request, file: UploadFile = File(...)):
    ruolo = request.session.get("ruolo", "")
    if ruolo != "admin":
        return HTMLResponse("Accesso negato", status_code=403)

    data = await file.read()
    if len(data) < 100:
        return HTMLResponse("File troppo piccolo o non valido", status_code=400)
    # Verifica magic bytes SQLite
    if not data[:16].startswith(b"SQLite format 3"):
        return HTMLResponse("File non è un database SQLite valido", status_code=400)

    bak = DB_PATH + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, bak)

    with open(DB_PATH, "wb") as f:
        f.write(data)

    return RedirectResponse("/amministrazione?msg=Database+importato+con+successo", status_code=303)
