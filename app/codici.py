"""
Modulo per la gestione e generazione automatica dei codici univoci:
- SKU Ingredienti: MAL-001, LUP-001, LIE-001, MIS-001, CHI-001, PAC-001
- Ricette: RIC-001, RIC-002...
- Cotte (Lotti di produzione): COT-YYYY-001, COT-YYYY-002...
"""
from datetime import datetime
import re
from typing import Any

try:
    from sqlalchemy.orm import Session
    from .models import CatalogoIngrediente, Ricetta, Cotta
except ImportError:
    Session = Any
    CatalogoIngrediente = Any
    Ricetta = Any
    Cotta = Any

PREFISSI_CATEGORIE = {
    # Malti e fermentabili
    "malto": "MAL",
    "malti": "MAL",
    "grain": "MAL",
    "grano": "MAL",
    "fermentable": "MAL",
    "fermentabili": "MAL",
    "estratto": "MAL",
    "fiocchi": "MAL",
    # Luppoli
    "luppolo": "LUP",
    "luppoli": "LUP",
    "hop": "LUP",
    "hops": "LUP",
    # Lieviti
    "lievito": "LIE",
    "lieviti": "LIE",
    "yeast": "LIE",
    # Spezie, aromi, additivi e zuccheri
    "spezia": "MIS",
    "spezie": "MIS",
    "aroma": "MIS",
    "aromi": "MIS",
    "misc": "MIS",
    "additivo": "MIS",
    "additivi": "MIS",
    "zucchero": "MIS",
    "zuccheri": "MIS",
    # Trattamento acqua e chimici pulizia
    "chimico": "CHI",
    "chimici": "CHI",
    "acqua": "CHI",
    "sali": "CHI",
    "acido": "CHI",
    # Packaging
    "packaging": "PAC",
    "bottiglia": "PAC",
    "bottiglie": "PAC",
    "tappo": "PAC",
    "tappi": "PAC",
    "fusto": "PAC",
    "fusti": "PAC",
    "cartone": "PAC",
    "cartoni": "PAC",
}


def prefisso_per_categoria(cat: str) -> str:
    c = (cat or "").strip().lower()
    for k, p in PREFISSI_CATEGORIE.items():
        if k in c:
            return p
    return "MIS"


def genera_prossimo_sku(categoria: str, db: Session) -> str:
    """Genera il prossimo codice SKU univoco progressivo (es. MAL-042)."""
    prefisso = prefisso_per_categoria(categoria)
    esistenti = (
        db.query(CatalogoIngrediente.codice)
        .filter(CatalogoIngrediente.codice.like(f"{prefisso}-%"))
        .all()
    )
    max_num = 0
    pattern = re.compile(rf"^{prefisso}-(\d+)$")
    for (cod,) in esistenti:
        if cod:
            m = pattern.match(cod.strip())
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    return f"{prefisso}-{max_num + 1:03d}"


def genera_prossimo_codice_ricetta(db: Session) -> str:
    """Genera il prossimo codice ricetta progressivo (es. RIC-013)."""
    esistenti = (
        db.query(Ricetta.codice)
        .filter(Ricetta.codice.like("RIC-%"))
        .all()
    )
    max_num = 0
    pattern = re.compile(r"^RIC-(\d+)$")
    for (cod,) in esistenti:
        if cod:
            m = pattern.match(cod.strip())
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    return f"RIC-{max_num + 1:03d}"


def genera_prossimo_codice_cotta(anno: int = None, db: Session = None) -> str:
    """Genera il prossimo codice cotta progressivo annuale (es. COT-2026-001)."""
    if not anno:
        anno = datetime.now().year
    prefisso = f"COT-{anno}"
    esistenti = (
        db.query(Cotta.codice)
        .filter(Cotta.codice.like(f"{prefisso}-%"))
        .all()
    )
    max_num = 0
    pattern = re.compile(rf"^COT-{anno}-(\d+)$")
    for (cod,) in esistenti:
        if cod:
            m = pattern.match(cod.strip())
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    return f"{prefisso}-{max_num + 1:03d}"
