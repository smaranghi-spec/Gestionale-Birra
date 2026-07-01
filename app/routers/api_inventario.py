"""API JSON per autocomplete inventario negli ordini di acquisto."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import SessionLocal
from ..models import InventarioItem

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/api/inventario/cerca")
def cerca_inventario(q: str = "", limit: int = 15, db: Session = Depends(get_db)):
    items = (
        db.query(InventarioItem)
        .filter(InventarioItem.nome.ilike(f"%{q}%"))
        .order_by(InventarioItem.nome)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": i.id,
            "nome": i.nome,
            "categoria": i.categoria,
            "unita": i.unita,
            "prezzo_unitario": i.prezzo_unitario,
            "quantita": i.quantita,
        }
        for i in items
    ]
