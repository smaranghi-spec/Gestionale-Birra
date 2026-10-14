import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..db import SessionLocal
from ..models import InventarioItem, EventoCalendario, Cotta, Impostazioni

router = APIRouter()
logger = logging.getLogger("api_notifiche")


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _parse_date_safe(val):
    """Estrae in modo sicuro un oggetto datetime gestendo ISO, YYYY-MM-DD, DD/MM/YYYY, o None."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    if hasattr(val, "year") and hasattr(val, "month") and hasattr(val, "day"):
        return datetime(val.year, val.month, val.day)
    val_str = str(val).strip()
    if not val_str:
        return None

    # Tenta parsing ISO (es: 2026-10-14T19:00:00 o 2026-10-14)
    try:
        iso_clean = val_str.replace("Z", "").split("+")[0]
        return datetime.fromisoformat(iso_clean)
    except Exception:
        pass

    # Formati standard comuni
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(val_str, fmt)
        except Exception:
            pass

    # Fallback estrazione prefisso data YYYY-MM-DD
    try:
        pref = val_str.split("T")[0].split(" ")[0]
        return datetime.strptime(pref, "%Y-%m-%d")
    except Exception:
        pass

    return None


@router.get("/api/notifiche")
def get_notifiche(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return {"notifiche": [], "backup_urgente": False, "giorni_da_backup": 0}

    try:
        notifiche = []
        oggi = datetime.now()
        oggi_str = oggi.strftime("%Y-%m-%d")
        tra_3_giorni = (oggi + timedelta(days=3)).strftime("%Y-%m-%d")

        # 1. Scorte in esaurimento (Inventario)
        try:
            inventario = db.query(InventarioItem).filter(
                InventarioItem.quantita_minima > 0,
                InventarioItem.quantita <= InventarioItem.quantita_minima
            ).all()

            for item in inventario:
                notifiche.append({
                    "tipo": "inventario",
                    "titolo": f"Scorta in esaurimento: {item.nome}",
                    "messaggio": f"Rimasti {item.quantita} {item.unita} (Soglia: {item.quantita_minima})",
                    "link": "/inventario",
                    "colore": "var(--red)"
                })
        except Exception as e:
            logger.warning(f"Errore controllo scorte inventario: {e}")

        # 1b. Controllo scadenze lotti inventario
        try:
            items_con_scadenza = db.query(InventarioItem).filter(
                InventarioItem.data_scadenza.isnot(None),
                InventarioItem.data_scadenza != ""
            ).all()

            for item in items_con_scadenza:
                d_scad = _parse_date_safe(item.data_scadenza)
                if d_scad:
                    diff = (d_scad.date() - oggi.date()).days
                    if 0 <= diff <= 7:
                        notifiche.append({
                            "tipo": "inventario",
                            "titolo": f"Scadenza imminente: {item.nome}",
                            "messaggio": f"Scade tra {diff} giorni ({item.data_scadenza})",
                            "link": "/inventario",
                            "colore": "var(--amber)"
                        })
                    elif diff < 0:
                        notifiche.append({
                            "tipo": "inventario",
                            "titolo": f"Ingrediente Scaduto: {item.nome}",
                            "messaggio": f"Scaduto il {item.data_scadenza}",
                            "link": "/inventario",
                            "colore": "var(--red)"
                        })
        except Exception as e:
            logger.warning(f"Errore controllo scadenze inventario: {e}")

        # 2. Appuntamenti e Task nel calendario (oggi e prossimi 3 gg)
        try:
            eventi = db.query(EventoCalendario).filter(
                EventoCalendario.data >= oggi_str,
                EventoCalendario.data <= tra_3_giorni
            ).order_by(EventoCalendario.data).all()

            for ev in eventi:
                quando = "Oggi" if ev.data == oggi_str else f"il {ev.data}"
                notifiche.append({
                    "tipo": "calendario",
                    "titolo": f"Calendario: {ev.titolo}",
                    "messaggio": f"In programma {quando} alle {ev.ora_inizio or ''}",
                    "link": "/calendario",
                    "colore": "var(--amber)"
                })
        except Exception as e:
            logger.warning(f"Errore controllo eventi calendario: {e}")

        # 3. Allerte Cotte (fermentazioni lunghe, pianificazioni scadute)
        try:
            cotte_attive = db.query(Cotta).filter(
                Cotta.stato.notin_(["pronta", "archiviata"])
            ).all()

            for cotta in cotte_attive:
                if cotta.stato == "pianificata" and cotta.data_brew:
                    d_brew = _parse_date_safe(cotta.data_brew)
                    if d_brew and d_brew.date() < oggi.date():
                        notifiche.append({
                            "tipo": "cotta",
                            "titolo": f"Cotta in ritardo: {cotta.nome}",
                            "messaggio": f"Era pianificata per il {cotta.data_brew}",
                            "link": f"/cotte/{cotta.id}",
                            "colore": "var(--red)"
                        })
                elif cotta.stato == "fermentazione" and cotta.data_inoculo:
                    d_inoc = _parse_date_safe(cotta.data_inoculo)
                    if d_inoc:
                        giorni_fermentazione = (oggi.date() - d_inoc.date()).days
                        if giorni_fermentazione >= 14:
                            notifiche.append({
                                "tipo": "cotta",
                                "titolo": f"Fine Fermentazione: {cotta.nome}",
                                "messaggio": f"In fermentazione da {giorni_fermentazione} giorni. Verifica la densità.",
                                "link": f"/cotte/{cotta.id}",
                                "colore": "var(--blue)"
                            })
        except Exception as e:
            logger.warning(f"Errore controllo cotte attive: {e}")

        # 4. Controllo Backup
        backup_urgente = False
        giorni_da_backup = 0
        try:
            imp = db.query(Impostazioni).filter(Impostazioni.chiave == "ultimo_backup").first()
            if imp and imp.valore:
                d_backup = _parse_date_safe(imp.valore)
                if d_backup:
                    giorni_da_backup = (oggi.date() - d_backup.date()).days
                else:
                    giorni_da_backup = 999
            else:
                giorni_da_backup = 999

            if giorni_da_backup >= 30:
                backup_urgente = True
        except Exception as e:
            logger.warning(f"Errore controllo data backup: {e}")
            backup_urgente = False
            giorni_da_backup = 0

        return {
            "notifiche": notifiche,
            "backup_urgente": backup_urgente,
            "giorni_da_backup": giorni_da_backup
        }
    except Exception as e:
        logger.error(f"Errore non gestito in get_notifiche: {e}")
        return {
            "notifiche": [],
            "backup_urgente": False,
            "giorni_da_backup": 0
        }
