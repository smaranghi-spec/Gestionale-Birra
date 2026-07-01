"""Importa ordine da foto o PDF tramite Gemini Vision."""
import base64
import json
import os
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


async def _gemini_vision_parse(data: bytes, mime_type: str = "image/jpeg") -> tuple:
    """Usa Gemini Vision per estrarre articoli da una foto/PDF."""
    import httpx

    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return [], "GEMINI_API_KEY non configurata nei Secrets."

    b64 = base64.b64encode(data).decode()
    prompt = (
        "Analizza questa immagine. È una fattura, un documento d'ordine o uno scontrino.\n"
        "Estrai ogni prodotto/articolo e restituisci SOLO un JSON array con questa struttura:\n"
        '[{"nome": "nome prodotto", "quantita": 1.0, "unita": "kg", '
        '"prezzo_unitario": 0.0, "categoria": "ingrediente"}]\n\n'
        "Categorie possibili: ingrediente, consumabile, packaging, chimico, altro.\n"
        "Unità possibili: kg, g, L, mL, pz.\n"
        "Se non riesci a determinare un valore, usa null.\n"
        "Rispondi SOLO con il JSON array, nessun testo aggiuntivo."
    )

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
                json={
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": mime_type, "data": b64}},
                        ]
                    }],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
                },
            )
        resp_data = resp.json()
        if "error" in resp_data:
            return [], f"Errore Gemini: {resp_data['error'].get('message', str(resp_data['error']))}"

        text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            righe = json.loads(m.group(0))
            out = []
            for r in righe[:30]:
                nome = (r.get("nome") or "").strip()
                if not nome or len(nome) < 2:
                    continue
                try:
                    qty = float(r.get("quantita") or 1)
                except Exception:
                    qty = 1.0
                unita = (r.get("unita") or "pz").strip().lower()
                try:
                    pu = float(r.get("prezzo_unitario") or 0) or None
                except Exception:
                    pu = None
                out.append({
                    "nome": nome[:80],
                    "quantita": qty,
                    "unita": unita,
                    "prezzo_unitario": pu,
                    "categoria": r.get("categoria") or "ingrediente",
                })
            return out, ""
        return [], f"Risposta non valida:\n{text[:400]}"
    except Exception as e:
        return [], f"Errore connessione: {str(e)[:200]}"


def _pdf_first_page_png(data: bytes) -> tuple:
    """Converte prima pagina PDF in PNG per Gemini Vision."""
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        pix = doc[0].get_pixmap(dpi=150)
        return pix.tobytes("png"), "image/png"
    except Exception:
        return data, "image/png"


@router.get("/acquisti/importa-foto", response_class=HTMLResponse)
def form_importa(request: Request):
    return templates.TemplateResponse(request, "acquisti_importa_foto.html", {
        "session": request.session,
        "righe": [],
        "errore": None,
    })


@router.post("/acquisti/importa-foto", response_class=HTMLResponse)
async def processa_foto(request: Request, file: UploadFile = File(...)):
    data = await file.read()
    fname = (file.filename or "").lower()

    if fname.endswith(".pdf"):
        img_bytes, mime = _pdf_first_page_png(data)
    elif fname.endswith(".png"):
        img_bytes, mime = data, "image/png"
    elif fname.endswith(".webp"):
        img_bytes, mime = data, "image/webp"
    else:
        img_bytes, mime = data, "image/jpeg"

    righe, errore = await _gemini_vision_parse(img_bytes, mime)

    return templates.TemplateResponse(request, "acquisti_importa_foto.html", {
        "righe": righe,
        "errore": errore or None,
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
        note="Importato da foto/PDF tramite Gemini AI",
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
