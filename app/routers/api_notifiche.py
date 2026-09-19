from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..db import SessionLocal
from ..models import InventarioItem, EventoCalendario, Cotta

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/api/notifiche")
def get_notifiche(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user_id"):
        return {"notifiche": []}

    notifiche = []
    oggi = datetime.now()
    oggi_str = oggi.strftime("%Y-%m-%d")
    tra_3_giorni = (oggi + timedelta(days=3)).strftime("%Y-%m-%d")

    # 1. Scorte in esaurimento (Inventario)
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

    # 2. Appuntamenti e Task nel calendario (oggi e prossimi 3 gg)
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

    # 3. Allerte Cotte (es. fermentazioni lunghe, pianificazioni scadute)
    cotte_attive = db.query(Cotta).filter(
        Cotta.stato.notin_(["pronta", "archiviata"])
    ).all()

    for cotta in cotte_attive:
        if cotta.stato == "pianificata" and cotta.data_brew and cotta.data_brew < oggi_str:
            notifiche.append({
                "tipo": "cotta",
                "titolo": f"Cotta in ritardo: {cotta.nome}",
                "messaggio": f"Era pianificata per il {cotta.data_brew}",
                "link": f"/cotte/{cotta.id}",
                "colore": "var(--red)"
            })
        elif cotta.stato == "fermentazione" and cotta.data_inoculo:
            try:
                data_inoc = datetime.strptime(cotta.data_inoculo, "%Y-%m-%d")
                giorni_fermentazione = (oggi - data_inoc).days
                if giorni_fermentazione >= 14:
                    notifiche.append({
                        "tipo": "cotta",
                        "titolo": f"Fine Fermentazione: {cotta.nome}",
                        "messaggio": f"In fermentazione da {giorni_fermentazione} giorni. Verifica la densità.",
                        "link": f"/cotte/{cotta.id}",
                        "colore": "var(--blue)"
                    })
            except ValueError:
                pass

    return {"notifiche": notifiche}
