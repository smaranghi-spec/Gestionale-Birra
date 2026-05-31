"""
Scanner fatture / bolle di acquisto.
Accetta PDF o immagine, estrae le righe acquistate.
"""
import os
import base64
import io
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ALLOWED_TYPES = {
    "application/pdf", "image/jpeg", "image/png", "image/webp",
    "image/jpg", "application/octet-stream",
}


def _extract_pdf_text(data: bytes) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts)


def _parse_text_to_righe(text: str) -> list[dict]:
    """
    Parsing euristico del testo della fattura.
    Cerca righe con: descrizione, quantità, prezzo unitario, totale.
    """
    import re
    righe = []
    lines = text.split("\n")
    price_pattern = re.compile(
        r"(\d{1,5}(?:[.,]\d{1,3})?)\s*(?:kg|g|l|ml|lt|pz|pcs|conf|bot)?\s+"
        r"(\d{1,5}(?:[.,]\d{1,2})?)\s+(\d{1,5}(?:[.,]\d{1,2})?)",
        re.IGNORECASE,
    )
    for line in lines:
        line = line.strip()
        if len(line) < 6:
            continue
        m = price_pattern.search(line)
        if m:
            # prendi la descrizione (parte prima dei numeri)
            desc = line[:m.start()].strip().rstrip(".:,;")
            if len(desc) < 3:
                continue
            try:
                qty = float(m.group(1).replace(",", "."))
                pu = float(m.group(2).replace(",", "."))
                totale = float(m.group(3).replace(",", "."))
            except ValueError:
                continue
            if pu > 0 and totale > 0:
                righe.append({
                    "descrizione": desc,
                    "quantita": qty,
                    "prezzo_unitario": pu,
                    "totale": totale,
                    "unita": "",
                })
    return righe


async def _extract_with_ai(data: bytes, filename: str, mime: str) -> list[dict]:
    """Usa GPT-4o mini vision per estrarre righe dalla fattura."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return []
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)

        if "pdf" in mime or filename.lower().endswith(".pdf"):
            text = _extract_pdf_text(data)
            content = [{"type": "text", "text": f"Fattura (testo estratto):\n\n{text[:4000]}"}]
        else:
            b64 = base64.b64encode(data).decode()
            content = [
                {"type": "text", "text": "Analizza questa fattura/bolla di acquisto."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]

        prompt = """Sei un assistente per birrifici artigianali. Analizza la fattura e restituisci SOLO un JSON array con le righe di acquisto.
Ogni oggetto deve avere ESATTAMENTE questi campi:
- "descrizione": nome del prodotto (string)
- "quantita": quantità numerica (number)
- "unita": unità di misura (string, es: "kg", "g", "pz", "l")
- "prezzo_unitario": prezzo per unità (number, in EUR, 0 se non disponibile)
- "totale": importo totale della riga (number, in EUR, 0 se non disponibile)

Ignora righe di intestazione, sconti, spese di spedizione, IVA, totali.
Restituisci SOLO il JSON array, senza testo aggiuntivo."""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
            max_tokens=2000,
            temperature=0,
        )
        import json
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        return [{"_errore_ai": str(e)}]


@router.get("/fattura", response_class=HTMLResponse)
def pagina_fattura(request: Request):
    has_ai = bool(os.environ.get("OPENAI_API_KEY"))
    return templates.TemplateResponse(request, "fattura.html", {
        "righe": None,
        "filename": None,
        "has_ai": has_ai,
        "errore": None,
    })


@router.post("/fattura", response_class=HTMLResponse)
async def scan_fattura(
    request: Request,
    file: UploadFile = File(...),
):
    has_ai = bool(os.environ.get("OPENAI_API_KEY"))
    filename = file.filename or "documento"
    mime = file.content_type or "application/octet-stream"

    if not any(t in mime for t in ["pdf", "image", "jpeg", "png", "webp"]):
        if not filename.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".webp")):
            return templates.TemplateResponse(request, "fattura.html", {
                "righe": None, "filename": filename, "has_ai": has_ai,
                "errore": "Formato non supportato. Carica un PDF o un'immagine (JPG, PNG, WebP).",
            })

    data = await file.read()

    righe = []
    errore = None

    # Prova AI se disponibile
    if has_ai:
        righe = await _extract_with_ai(data, filename, mime)
        if righe and "_errore_ai" in (righe[0] if righe else {}):
            errore = f"AI: {righe[0]['_errore_ai']}"
            righe = []

    # Fallback: parsing euristico da testo PDF
    if not righe and ("pdf" in mime or filename.lower().endswith(".pdf")):
        try:
            text = _extract_pdf_text(data)
            righe = _parse_text_to_righe(text)
            if not righe:
                errore = (errore or "") + " Il PDF è stato letto ma non sono stati rilevati automaticamente articoli con prezzi. Compila la tabella manualmente."
        except Exception as e:
            errore = f"Errore lettura PDF: {e}"

    # Per immagini senza AI: lascia righe vuote + mostra immagine
    is_image = any(t in mime for t in ["image", "jpeg", "png", "webp"]) or filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    img_b64 = None
    if is_image:
        img_b64 = base64.b64encode(data).decode()
        if not has_ai and not righe:
            errore = "Configura OPENAI_API_KEY per estrarre automaticamente i dati dalle immagini. Puoi compilare la tabella manualmente."

    return templates.TemplateResponse(request, "fattura.html", {
        "righe": righe,
        "filename": filename,
        "has_ai": has_ai,
        "errore": errore,
        "img_b64": img_b64,
        "img_mime": mime if is_image else None,
    })
