from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .db import engine
from .models import Base
from .routers import ricette, catalogo, ingredienti, stili, cotte, importa

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gestionale Birrificio")

app.include_router(ricette.router)
app.include_router(catalogo.router)
app.include_router(ingredienti.router)
app.include_router(stili.router)
app.include_router(cotte.router)
app.include_router(importa.router)


@app.get("/")
def home():
    return RedirectResponse("/ricette/html")