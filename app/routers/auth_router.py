from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from ..db import SessionLocal
from ..models import Utente
from ..auth import hash_password, verify_password

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    n_utenti = db.query(Utente).count()
    return templates.TemplateResponse(request, "login.html", {
        "errore": None,
        "primo_accesso": n_utenti == 0,
    })


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    utente = db.query(Utente).filter(Utente.username == username, Utente.attivo == 1).first()
    if not utente or not verify_password(password, utente.password_hash):
        n_utenti = db.query(Utente).count()
        return templates.TemplateResponse(request, "login.html", {
            "errore": "Username o password non corretti.",
            "primo_accesso": n_utenti == 0,
        })
    request.session["user_id"] = utente.id
    request.session["username"] = utente.username
    request.session["nome"] = utente.nome or utente.username
    request.session["ruolo"] = utente.ruolo
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    n_utenti = db.query(Utente).count()
    ruolo_session = request.session.get("ruolo", "")
    if n_utenti > 0 and ruolo_session != "admin":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "register.html", {"errore": None})


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    nome: str = Form(""),
    db: Session = Depends(get_db),
):
    n_utenti = db.query(Utente).count()
    ruolo_session = request.session.get("ruolo", "")
    if n_utenti > 0 and ruolo_session != "admin":
        return RedirectResponse("/login", status_code=303)

    existing = db.query(Utente).filter(Utente.username == username).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {
            "errore": "Username già in uso. Scegli un altro username."
        })

    ruolo = "admin" if n_utenti == 0 else "birraio"
    utente = Utente(
        username=username,
        password_hash=hash_password(password),
        nome=nome.strip() or username,
        ruolo=ruolo,
        attivo=1,
        data_creazione=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    db.add(utente)
    db.commit()
    db.refresh(utente)
    request.session["user_id"] = utente.id
    request.session["username"] = utente.username
    request.session["nome"] = utente.nome
    request.session["ruolo"] = utente.ruolo
    return RedirectResponse("/", status_code=303)


@router.get("/utenti", response_class=HTMLResponse)
def gestisci_utenti(request: Request, db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    utenti = db.query(Utente).order_by(Utente.id).all()
    return templates.TemplateResponse(request, "utenti.html", {
        "utenti": utenti,
        "session": request.session,
    })


@router.post("/utenti/{uid}/toggle")
def toggle_utente(uid: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    utente = db.query(Utente).filter(Utente.id == uid).first()
    if utente and utente.id != request.session.get("user_id"):
        utente.attivo = 0 if utente.attivo else 1
        db.commit()
    return RedirectResponse("/utenti", status_code=303)
