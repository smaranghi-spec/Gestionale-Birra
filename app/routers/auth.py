import json
from datetime import datetime
from passlib.context import CryptContext
from fastapi import Request
from sqlalchemy.orm import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def get_current_user_from_session(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    from .models import Utente
    return db.query(Utente).filter(Utente.id == user_id, Utente.attivo == 1).first()


def snapshot_ricetta(ricetta) -> dict:
    return {
        "id": ricetta.id,
        "nome": ricetta.nome,
        "tipo": ricetta.tipo,
        "volume_target_litri": ricetta.volume_target_litri,
        "efficienza": ricetta.efficienza,
        "versione": ricetta.versione,
        "stile_id": ricetta.stile_id,
        "note": ricetta.note,
    }


def snapshot_ingrediente(i) -> dict:
    return {
        "id": i.id,
        "ricetta_id": i.ricetta_id,
        "nome": i.nome,
        "categoria": i.categoria,
        "quantita": i.quantita,
        "unita": i.unita,
        "note": i.note,
        "time_min": i.time_min,
        "prezzo_unitario": i.prezzo_unitario,
        "fermentable_type": i.fermentable_type,
        "yield_percent": i.yield_percent,
        "color_srm": i.color_srm,
        "alpha_acid": i.alpha_acid,
        "hop_use": i.hop_use,
        "hop_form": i.hop_form,
        "attenuation": i.attenuation,
        "yeast_type": i.yeast_type,
        "yeast_form": i.yeast_form,
        "misc_type": i.misc_type,
        "misc_use": i.misc_use,
    }


def log_modifica(db, request, entita_tipo: str, entita_id: int, azione: str,
                 prima: dict = None, dopo: dict = None, descrizione: str = None):
    from .models import LogModifica
    user_id = request.session.get("user_id") if request and hasattr(request, "session") else None
    username = request.session.get("username") if request and hasattr(request, "session") else "sistema"
    entry = LogModifica(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        utente_id=user_id,
        username=username or "anonimo",
        entita_tipo=entita_tipo,
        entita_id=entita_id,
        azione=azione,
        snapshot_prima=json.dumps(prima, ensure_ascii=False, default=str) if prima else None,
        snapshot_dopo=json.dumps(dopo, ensure_ascii=False, default=str) if dopo else None,
        descrizione=descrizione,
    )
    db.add(entry)
