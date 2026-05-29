from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .db import engine
from .models import Base
from .routers import ricette, catalogo, ingredienti, stili, cotte, importa, acquisti

Base.metadata.create_all(bind=engine)

templates = Jinja2Templates(directory="templates")


def run_migrations():
    import sqlite3

    conn = sqlite3.connect("./gestionale_birra.db")
    for sql in [
        "ALTER TABLE ingredienti_ricetta ADD COLUMN prezzo_unitario REAL",
    ]:
        try:
            conn.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()


run_migrations()

app = FastAPI(title="Gestionale Birrificio")

app.include_router(ricette.router)
app.include_router(catalogo.router)
app.include_router(ingredienti.router)
app.include_router(stili.router)
app.include_router(cotte.router)
app.include_router(importa.router)
app.include_router(acquisti.router)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
