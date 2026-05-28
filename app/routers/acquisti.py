from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/acquisti", response_class=HTMLResponse)
def pagina_acquisti(request: Request):
    return templates.TemplateResponse("acquisti.html", {"request": request})
