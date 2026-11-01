import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import Cotta, LogCotta

router = APIRouter(prefix="/api/iot", tags=["IoT"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


@router.post("/ispindel/{cotta_id}")
async def ispindel_webhook(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Riceve telemetria dal densimetro digitale iSpindel.
    Payload standard:
    { "name": "iSpindel01", "temperature": 19.5, "temp_units": "C", "gravity": 1.042, "battery": 4.12, "angle": 45.3 }
    """
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return JSONResponse({"error": "Cotta non trovata"}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON non valido"}, status_code=400)

    # Estrazione gravità (supporta sia SG 1.042 che Gradi Plato 10.5)
    raw_gravity = data.get("gravity") or data.get("densita")
    raw_temp = data.get("temperature") or data.get("temp")
    temp_units = str(data.get("temp_units") or "C").upper()

    temp_c = None
    if raw_temp is not None:
        try:
            t = float(raw_temp)
            temp_c = round((t - 32) * 5 / 9, 1) if temp_units == "F" else round(t, 1)
        except (ValueError, TypeError):
            pass

    sg = None
    if raw_gravity is not None:
        try:
            g = float(raw_gravity)
            # Se inviato in plato (> 3.0), converti in SG approssimato
            if g > 3.0:
                sg = round(1.0 + (g / (258.6 - (g / 258.2) * 227.1)), 3)
            else:
                sg = round(g, 3)
        except (ValueError, TypeError):
            pass

    # Aggiorna cotta
    if sg:
        cotta.fg_reale = sg
    if temp_c:
        cotta.temp_fermentazione = temp_c

    # Inserisci nel log cotta per tracciamento storico e grafico
    desc = f"iSpindel: {sg or '—'} SG · {temp_c or '—'}°C"
    if data.get("battery"):
        desc += f" (Batt: {data.get('battery')}V)"

    log_entry = LogCotta(
        cotta_id=cotta_id,
        timestamp=_now_str(),
        fase=cotta.stato or "fermentazione",
        tipo="iot_telemetria",
        descrizione=desc,
        valore=sg,
        unita="SG",
        note=json.dumps(data),
    )
    db.add(log_entry)
    db.commit()

    return {
        "status": "ok",
        "cotta_id": cotta_id,
        "gravity": sg,
        "temperature_c": temp_c,
        "device": data.get("name", "iSpindel"),
    }


@router.post("/tilt/{cotta_id}")
async def tilt_webhook(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Riceve telemetria da Tilt Hydrometer (TiltBridge o Tilt Pi).
    Payload: { "Color": "RED", "SG": 1.042, "Temp": 68.0, "Time": 16999999 }
    """
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return JSONResponse({"error": "Cotta non trovata"}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON non valido"}, status_code=400)

    raw_sg = data.get("SG") or data.get("gravity")
    raw_temp = data.get("Temp") or data.get("temp")

    sg = round(float(raw_sg), 3) if raw_sg else None
    temp_c = None
    if raw_temp is not None:
        t = float(raw_temp)
        temp_c = round((t - 32) * 5 / 9, 1) if t > 40 else round(t, 1)

    if sg:
        cotta.fg_reale = sg
    if temp_c:
        cotta.temp_fermentazione = temp_c

    desc = f"Tilt ({data.get('Color','')}): {sg or '—'} SG · {temp_c or '—'}°C"
    log_entry = LogCotta(
        cotta_id=cotta_id,
        timestamp=_now_str(),
        fase=cotta.stato or "fermentazione",
        tipo="iot_telemetria",
        descrizione=desc,
        valore=sg,
        unita="SG",
        note=json.dumps(data),
    )
    db.add(log_entry)
    db.commit()

    return {"status": "ok", "cotta_id": cotta_id, "gravity": sg, "temp_c": temp_c}


@router.post("/generic/{cotta_id}")
async def generic_iot_webhook(cotta_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Endpoint universale per RAPT Pill, Graviator, Nautilis o script custom.
    Accetta: { "gravity": 1.045, "temperature": 18.5, "device": "RAPT_Pill" }
    """
    cotta = db.query(Cotta).filter(Cotta.id == cotta_id).first()
    if not cotta:
        return JSONResponse({"error": "Cotta non trovata"}, status_code=404)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON non valido"}, status_code=400)

    sg = float(data.get("gravity") or data.get("sg") or 0) or None
    temp = float(data.get("temperature") or data.get("temp") or 0) or None

    if sg:
        cotta.fg_reale = round(sg, 3)
    if temp:
        cotta.temp_fermentazione = round(temp, 1)

    log_entry = LogCotta(
        cotta_id=cotta_id,
        timestamp=_now_str(),
        fase=cotta.stato or "fermentazione",
        tipo="iot_telemetria",
        descrizione=f"{data.get('device', 'IoT')}: {sg or '—'} SG · {temp or '—'}°C",
        valore=sg,
        unita="SG",
        note=json.dumps(data),
    )
    db.add(log_entry)
    db.commit()

    return {"status": "ok", "cotta_id": cotta_id, "gravity": sg, "temp": temp}


@router.get("/telemetria/{cotta_id}")
def get_telemetria_cotta(cotta_id: int, db: Session = Depends(get_db)):
    """
    Restituisce i punti storici di telemetria per plottare il grafico di fermentazione.
    """
    logs = (
        db.query(LogCotta)
        .filter(LogCotta.cotta_id == cotta_id, LogCotta.tipo == "iot_telemetria")
        .order_by(LogCotta.id.asc())
        .all()
    )

    punti = []
    for l in logs:
        punti.append({
            "timestamp": l.timestamp,
            "valore": l.valore,
            "descrizione": l.descrizione,
        })
    return {"cotta_id": cotta_id, "punti": punti}
