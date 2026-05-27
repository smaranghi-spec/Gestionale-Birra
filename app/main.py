from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Gestionale Birrificio")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/ricette/html", response_class=HTMLResponse)
def elenco_ricette(request: Request):
    return templates.TemplateResponse("ricette.html", {"request": request, "ricette": []})


@app.get("/catalogo-ingredienti/html", response_class=HTMLResponse)
def catalogo_ingredienti(request: Request):
    return templates.TemplateResponse(
        "catalogo_ingredienti.html",
        {"request": request, "items": [], "categoria_attiva": None, "ricetta_id": None}
    )


@app.get("/catalogo/ingredienti/nuovo", response_class=HTMLResponse)
def nuovo_ingrediente(request: Request):
    return templates.TemplateResponse("nuovo_ingrediente_catalogo.html", {"request": request})


@app.get("/acquisti", response_class=HTMLResponse)
def acquisti(request: Request):
    return templates.TemplateResponse("acquisti.html", {"request": request})


@app.get("/produzione", response_class=HTMLResponse)
def produzione(request: Request):
    return templates.TemplateResponse("produzione.html", {"request": request})


@app.get("/magazzino", response_class=HTMLResponse)
def magazzino(request: Request):
    return templates.TemplateResponse("magazzino.html", {"request": request})


@app.get("/imbottigliamento", response_class=HTMLResponse)
def imbottigliamento(request: Request):
    return templates.TemplateResponse("imbottigliamento.html", {"request": request})


@app.get("/vendite", response_class=HTMLResponse)
def vendite(request: Request):
    return templates.TemplateResponse("vendite.html", {"request": request})


@app.get("/amministrazione", response_class=HTMLResponse)
def amministrazione(request: Request):
    return templates.TemplateResponse("amministrazione.html", {"request": request})
