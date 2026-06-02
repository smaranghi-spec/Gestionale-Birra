"""Assistente AI per il gestionale birrificio usando Replit AI (OpenAI-compatible)."""
import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

SYSTEM_PROMPT = """Sei un mastro birraio esperto e assistente del gestionale birrificio.
Aiuti con:
- Risoluzione problemi durante la cotta (densità anomale, fermentazione bloccata, off-flavors)
- Calcoli birrari (IBU, ABV, EBC, efficienza, priming CO2)
- Scelta ingredienti, stili, profili acqua
- Gestione ricette e interpretazione parametri
- Suggerimenti su processi produttivi
Rispondi in italiano, in modo conciso e pratico. Se fai calcoli, mostra il procedimento."""


async def _call_ai(messages: list) -> str:
    try:
        import httpx
        api_key = os.environ.get("REPLIT_AI_KEY") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return "⚠️ Chiave AI non configurata. Contatta l'amministratore."

        base_url = "https://api.openai.com/v1"
        model = "gpt-4o-mini"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "max_tokens": 800, "temperature": 0.7},
            )
            data = resp.json()
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
            return f"Errore API: {data.get('error', {}).get('message', 'Risposta non valida')}"
    except Exception as e:
        return f"❌ Errore connessione AI: {str(e)[:100]}"


@router.post("/api/ai/chat")
async def ai_chat(request: Request):
    try:
        body = await request.json()
        domanda = (body.get("domanda") or "").strip()
        contesto = body.get("contesto", "")
        storico = body.get("storico", [])
    except Exception:
        return JSONResponse({"errore": "Payload non valido"}, status_code=400)

    if not domanda:
        return JSONResponse({"errore": "Domanda vuota"}, status_code=400)

    sys_content = SYSTEM_PROMPT
    if contesto:
        sys_content += f"\n\nContesto attuale:\n{contesto}"

    messages = [{"role": "system", "content": sys_content}]
    for m in storico[-6:]:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": domanda})

    risposta = await _call_ai(messages)
    return JSONResponse({"risposta": risposta})
