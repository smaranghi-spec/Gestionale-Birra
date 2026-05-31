from pathlib import Path
import hashlib
from datetime import datetime

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .db import Base, SessionLocal, engine

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

app = FastAPI(title="Gestionale Birrificio")
app.add_middleware(SessionMiddleware, secret_key="cambia-questa-chiave-subito")
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Attrezzatura(Base):
    __tablename__ = "attrezzature"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False, default="generico")
    descrizione = Column(Text)
    capacita_litri = Column(Float)
    ubicazione = Column(String)
    attiva = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(request=request, name="home.html", context={"title": "Dashboard", "user": user})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login", "error": None})


@app.post("/login", response_class=HTMLResponse)
def do_login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or user.password_hash != hash_password(password):
        return templates.TemplateResponse(request=request, name="login.html", context={"title": "Login", "error": "Credenziali non valide"}, status_code=401)
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/debug/seed-admin")
def seed_admin(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(username="admin", password_hash=hash_password("admin123"))
        db.add(user)
        db.commit()
    return {"ok": True, "username": "admin", "password": "admin123"}


@app.get("/attrezzature", response_class=HTMLResponse)
def lista_attrezzature(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    attrezzature = db.query(Attrezzatura).order_by(Attrezzatura.id.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="attrezzature.html",
        context={"title": "Attrezzature", "user": user, "attrezzature": attrezzature},
    )


@app.post("/attrezzature/nuova")
def nuova_attrezzatura(
    request: Request,
    nome: str = Form(...),
    tipo: str = Form("generico"),
    descrizione: str = Form(""),
    capacita_litri: float = Form(0),
    ubicazione: str = Form(""),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    a = Attrezzatura(
        nome=nome,
        tipo=tipo,
        descrizione=descrizione or None,
        capacita_litri=capacita_litri or None,
        ubicazione=ubicazione or None,
    )
    db.add(a)
    db.commit()
    return RedirectResponse(url="/attrezzature", status_code=303)
