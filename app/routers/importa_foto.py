"""Importa ordine da foto o PDF tramite OCR (pytesseract)."""
import io
import re
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import OrdineAcquisto, RigaOrdine

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ocr_from_image(data: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img, lang="ita+eng")
    except Exception as e:
        return f"[ERRORE OCR: {e}]"


def _ocr_from_pdf(data: bytes) -> str:
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=data, filetype="pdf")
        testo = ""
        for page in doc:
            testo += page.get_text()
        return testo
    except Exception as e:
        return f"[ERRORE PDF: {e}]"


def _parse_righe(testo: str) -> list:
    """Estrae righe prodotto da testo OCR grezzo. Heuristic-based."""
    righe = []
    lines = [l.strip() for l in testo.splitlines() if l.strip()]
    price_pattern = re.compile(r"(\d+[.,]\d{1,2})\s*€?$|€\s*(\d+[.,]\d{1,2})")
    qty_pattern = re.compile(r"(\d+[.,]?\d*)\s*(kg|g|L|ml|pz|pcs|bst|bot)", re.IGNORECASE)

    for line in lines:
        if len(line) < 4:
            continue
        price_m = price_pattern.search(line)
        qty_m = qty_pattern.search(line)
        prezzo = None
        quantita = None
        unita = "pz"
        if price_m:
            raw = price_m.group(1) or price_m.group(2)
            prezzo = float(raw.replace(",", "."))
        if qty_m:
            quantita = float(qty_m.group(1).replace(",", "."))
            unita = qty_m.group(2).lower()
        nome = re.sub(r"\d+[.,]\d{1,2}\s*€?", "", line).strip()
        nome = re.sub(r"€\s*\d+[.,]\d{1,2}", "", nome).strip()
        nome = re.sub(r"\d+[.,]?\d*\s*(kg|g|L|ml|pz|pcs)", "", nome, flags=re.IGNORECASE).strip()
        nome = nome.strip(".,;:-|")
        if nome and len(nome) > 2 and not nome.replace(" ", "").isdigit():
            righe.append({
                "nome": nome[:80],
                "quantita": quantita or 1.0,
                "unita": unita,
                "prezzo_unitario": prezzo,
                "categoria": "ingrediente",
            })
    return righe[:30]


@router.get("/acquisti/importa-foto", response_class=HTMLResponse)
def form_importa(request: Request):
    return templates.TemplateResponse(request, "acquisti_importa_foto.html", {
        "session": request.session,
    })


@router.post("/acquisti/importa-foto", response_class=HTMLResponse)
async def processa_foto(request: Request, file: UploadFile = File(...)):
    data = await file.read()
    fname = file.filename or ""
    if fname.lower().endswith(".pdf"):
        testo = _ocr_from_pdf(data)
    else:
        testo = _ocr_from_image(data)

    righe = _parse_righe(testo)
    return templates.TemplateResponse(request, "acquisti_importa_foto.html", {
        "testo_ocr": testo[:3000],
        "righe": righe,
        "session": request.session,
    })


@router.post("/acquisti/importa-foto/salva")
async def salva_importato(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    nomi = form.getlist("nome[]")
    quantita_l = form.getlist("quantita[]")
    unita_l = form.getlist("unita[]")
    prezzi_l = form.getlist("prezzo_unitario[]")
    cat_l = form.getlist("categoria[]")
    fornitore = form.get("fornitore", "")

    ordine = OrdineAcquisto(
        data=datetime.now().strftime("%Y-%m-%d"),
        fornitore=fornitore or None,
        stato="bozza",
        note="Importato da foto/PDF",
    )
    db.add(ordine)
    db.flush()

    totale = 0.0
    for i, nome in enumerate(nomi):
        nome = nome.strip()
        if not nome:
            continue
        try:
            qty = float(quantita_l[i].replace(",", ".") if i < len(quantita_l) else "1")
        except Exception:
            qty = 1.0
        try:
            pu = float(prezzi_l[i].replace(",", ".")) if i < len(prezzi_l) and prezzi_l[i].strip() else None
        except Exception:
            pu = None
        unita = unita_l[i] if i < len(unita_l) else "pz"
        cat = cat_l[i] if i < len(cat_l) else "ingrediente"
        totale += qty * (pu or 0)
        db.add(RigaOrdine(
            ordine_id=ordine.id, nome=nome, categoria=cat,
            quantita=qty, unita=unita, prezzo_unitario=pu,
        ))
    ordine.totale = round(totale, 2)
    db.commit()
    return RedirectResponse(f"/acquisti/{ordine.id}?msg=Ordine+importato+da+foto", status_code=303)
