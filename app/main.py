from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Gestionale Birrificio")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "ricette.html",
        {
            "request": request,
            "ricette": []
        }
    )


@app.get("/ricette/html", response_class=HTMLResponse)
def elenco_ricette(request: Request):
    return templates.TemplateResponse(
        "ricette.html",
        {
            "request": request,
            "ricette": []
        }
    )


@app.get("/catalogo-ingredienti/html", response_class=HTMLResponse)
def catalogo_ingredienti(request: Request):
    return templates.TemplateResponse(
        "catalogo_ingredienti.html",
        {
            "request": request,
            "ingredienti": []
        }
    )
