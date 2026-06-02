from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import User, ProfiloSocio

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


@router.post("/login-ospite")
def login_ospite(request: Request):
    request.session["user_id"] = 0
    request.session["username"] = "ospite"
    request.session["nome"] = "Ospite"
    request.session["ruolo"] = "ospite"
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "register.html", {
        "errore": None,
        "successo": False,
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
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse(request, "register.html", {
            "errore": "Username già in uso. Scegline un altro.",
            "successo": False,
            "session": request.session,
        })
    n = db.query(User).count()
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
    # Mostra conferma senza auto-login: l'utente va al login e poi diventa socio
    return templates.TemplateResponse(request, "register.html", {
        "errore": None,
        "successo": True,
        "nuovo_username": u.username,
        "session": {},
    })


@router.get("/utenti", response_class=HTMLResponse)
def gestisci_utenti(request: Request, msg: str = None, db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    utenti = db.query(User).order_by(User.id).all()
    # mappa user_id → ProfiloSocio
    soci_map = {s.user_id: s for s in db.query(ProfiloSocio).filter(ProfiloSocio.user_id.isnot(None)).all()}
    return templates.TemplateResponse(request, "utenti.html", {
        "utenti": utenti,
        "soci_map": soci_map,
        "msg": msg,
        "session": request.session,
    })


@router.post("/utenti/{uid}/ruolo")
def cambia_ruolo(uid: int, request: Request, ruolo: str = Form(...), db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    u = db.query(User).filter(User.id == uid).first()
    if u and u.id != request.session.get("user_id") and ruolo in ("admin", "socio", "birraio"):
        u.ruolo = ruolo
        db.commit()
    return RedirectResponse("/utenti?msg=Ruolo+aggiornato", status_code=303)


@router.get("/diventa-socio", response_class=HTMLResponse)
def diventa_socio_page(request: Request, db: Session = Depends(get_db)):
    uid = request.session.get("user_id")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    # Se è già socio o admin, reindirizza
    ruolo = request.session.get("ruolo", "")
    if ruolo in ("socio", "admin"):
        return RedirectResponse("/?msg=Sei+già+socio", status_code=303)
    u = db.query(User).filter(User.id == uid).first()
    # Controlla se ha già un profilo socio
    profilo = db.query(ProfiloSocio).filter(ProfiloSocio.user_id == uid).first()
    if profilo:
        return RedirectResponse(f"/soci/{profilo.id}?msg=Profilo+già+esistente", status_code=303)
    from datetime import datetime
    return templates.TemplateResponse(request, "diventa_socio.html", {
        "u": u,
        "anno_corrente": datetime.now().year,
        "session": request.session,
    })


@router.post("/diventa-socio")
def diventa_socio_submit(
    request: Request,
    nome: str = Form(...),
    cognome: str = Form(""),
    email: str = Form(""),
    telefono: str = Form(""),
    data_nascita: str = Form(""),
    codice_fiscale: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    from datetime import datetime
    uid = request.session.get("user_id")
    if not uid:
        return RedirectResponse("/login", status_code=303)
    # Controlla che non esista già
    if db.query(ProfiloSocio).filter(ProfiloSocio.user_id == uid).first():
        return RedirectResponse("/", status_code=303)
    s = ProfiloSocio(
        nome=nome.strip(),
        cognome=cognome.strip() or None,
        email=email.strip() or None,
        telefono=telefono.strip() or None,
        data_nascita=data_nascita or None,
        codice_fiscale=codice_fiscale.strip() or None,
        anno_iscrizione=datetime.now().year,
        stato_socio="attivo",
        note=note.strip() or None,
        user_id=uid,
    )
    db.add(s)
    u = db.query(User).filter(User.id == uid).first()
    if u and u.ruolo not in ("admin",):
        u.ruolo = "socio"
        u.nome = nome.strip() or u.nome
    db.commit()
    # Aggiorna la sessione in tempo reale
    request.session["ruolo"] = "socio"
    request.session["nome"] = u.nome if u else request.session.get("nome", "")
    return RedirectResponse("/?msg=Benvenuto+tra+i+soci!", status_code=303)


@router.post("/utenti/{uid}/toggle")
def toggle_utente(uid: int, request: Request, db: Session = Depends(get_db)):
    if request.session.get("ruolo") != "admin":
        return RedirectResponse("/", status_code=303)
    u = db.query(User).filter(User.id == uid).first()
    if u and u.id != request.session.get("user_id"):
        u.is_active = not u.is_active
        db.commit()
    return RedirectResponse("/utenti", status_code=303)
