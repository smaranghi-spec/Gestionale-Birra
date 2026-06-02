"""
Strumenti di calcolo per birrai:
IBU (Tinseth), ABV, colore EBC/SRM, correzione densità per temperatura,
priming CO2, conversione unità, calcolatore acqua (diluizione/trattamento).
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/strumenti", response_class=HTMLResponse)
def strumenti(request: Request):
    return templates.TemplateResponse(request, "strumenti.html", {
        "session": request.session,
    })
