from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from .db import engine
from .models import Base
from .routers import ricette, catalogo, ingredienti

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Gestionale Birrificio")

app.include_router(ricette.router)
app.include_router(catalogo.router)
app.include_router(ingredienti.router)


@app.get("/")
def home():
    return RedirectResponse("/ricette/html")