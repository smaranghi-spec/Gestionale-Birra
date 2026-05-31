from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .db import Base, SessionLocal, engine
from .models import Attrezzatura, Ricetta, User

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="Gestionale Birrificio")
app.add_middleware(SessionMiddleware, secret_key="cambia-questa-chiave-subito")
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


def login_required(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={"title": "Dashboard", "user": user},
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"title": "Login", "error": None},
    )


@app.post("/login", response_class=HTMLResponse)
def do_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"title": "Login", "error": "Credenziali non valide"},
            status_code=401,
        )

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
        user = User(username="admin", password_hash=pwd_context.hash("admin123"))
        db.add(user)
        db.commit()
    return {"ok": True, "username": "admin", "password": "admin123"}
