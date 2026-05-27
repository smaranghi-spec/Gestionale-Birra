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
        "home.html",
        {"request": request}
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
            "items": [],
            "categoria_attiva": None,
            "ricetta_id": None
        }
    )


@app.get("/catalogo/ingredienti/nuovo", response_class=HTMLResponse)
def nuovo_ingrediente(request: Request):
    return templates.TemplateResponse(
        "nuovo_ingrediente_catalogo.html",
        {"request": request}
    )


@app.get("/produzione", response_class=HTMLResponse)
def produzione(request: Request):
    return HTMLResponse("""
    <html><head><title>Produzione</title></head>
    <body style="font-family:Arial,sans-serif;margin:40px;background:#f7f3ee;">
        <h1 style="color:#5a381e;">Produzione</h1>
        <p>Sezione in preparazione.</p>
        <p><a href="/">Torna alla home</a></p>
    </body></html>
    """)


@app.get("/magazzino", response_class=HTMLResponse)
def magazzino(request: Request):
    return HTMLResponse("""
    <html><head><title>Magazzino</title></head>
    <body style="font-family:Arial,sans-serif;margin:40px;background:#f7f3ee;">
        <h1 style="color:#5a381e;">Magazzino</h1>
        <p>Sezione in preparazione.</p>
        <p><a href="/">Torna alla home</a></p>
    </body></html>
    """)


@app.get("/imbottigliamento", response_class=HTMLResponse)
def imbottigliamento(request: Request):
    return HTMLResponse("""
    <html><head><title>Imbottigliamento</title></head>
    <body style="font-family:Arial,sans-serif;margin:40px;background:#f7f3ee;">
        <h1 style="color:#5a381e;">Imbottigliamento</h1>
        <p>Sezione in preparazione.</p>
        <p><a href="/">Torna alla home</a></p>
    </body></html>
    """)


@app.get("/vendite", response_class=HTMLResponse)
def vendite(request: Request):
    return HTMLResponse("""
    <html><head><title>Vendite</title></head>
    <body style="font-family:Arial,sans-serif;margin:40px;background:#f7f3ee;">
        <h1 style="color:#5a381e;">Vendite</h1>
        <p>Sezione in preparazione.</p>
        <p><a href="/">Torna alla home</a></p>
    </body></html>
    """)


@app.get("/amministrazione", response_class=HTMLResponse)
def amministrazione(request: Request):
    return HTMLResponse("""
    <html><head><title>Amministrazione</title></head>
    <body style="font-family:Arial,sans-serif;margin:40px;background:#f7f3ee;">
        <h1 style="color:#5a381e;">Amministrazione</h1>
        <p>Sezione in preparazione.</p>
        <p><a href="/">Torna alla home</a></p>
    </body></html>
    """)
