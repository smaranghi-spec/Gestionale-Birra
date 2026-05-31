from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import User

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
        u = db.query(User).filter(User.id == request.session["user_id"]).first()
        if u and u.is_active:
            return RedirectResponse("/", status_code=303)
        request.session.clear()
    n = db.query(User).count()
    return templates.TemplateResponse(request, "login.html", {
        "errore": None,
        "primo_accesso": n == 0,
        "session": {},
    })


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not u or not u.check_pw(password):
        n = db.query(User).count()
        return templates.TemplateResponse(request, "login.html", {
            "errore": "Username o password non corretti.",
            "primo_accesso": n == 0,
            "session": {},
        })
    request.session["user_id"] = u.id
    request.session["username"] = u.username
    request.session["nome"] = u.nome or u.username
    request.session["ruolo"] = u.ruolo
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    n = db.query(User).count()
    if n > 0 and request.session.get("ruolo") != "admin":
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "register.html", {
        "errore": None,
        "session": request.session,
    })


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    nome: str = Form(""),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    n = db.query(User).count()
    if n > 0 and request.session.get("ruolo") != "admin":
        return RedirectResponse("/login", status_code=303)
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(request, "register.html", {
            "errore": "Username già in uso.",
            "session": request.session,
        })
    ruolo = "admin" if n == 0 else "birraio"
    u = User(
        username=username,
        password_hash=User.hash_pw(password),
        nome=nome.strip() or username,
        ruolo=ruolo,
        is_active=True,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    request.session["user_id"] = u.id
    request.session["username"] = u.username
    request.session["nome"] = u.nome
    request.session["ruolo"] = u.ruolo
    return RedirectResponse("/", status_code=303)


@router.get("/utenti", response_class=HTMLResponse)
def gestisci_utenti(request: Request, db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    utenti = db.query(User).order_by(User.id).all()
    return templates.TemplateResponse(request, "utenti.html", {
        "utenti": utenti,
        "session": request.session,
    })


@router.post("/utenti/{uid}/toggle")
def toggle_utente(uid: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    u = db.query(User).filter(User.id == uid).first()
    if u and u.id != request.session.get("user_id"):
        u.is_active = not u.is_active
        db.commit()
    return RedirectResponse("/utenti", status_code=303)
