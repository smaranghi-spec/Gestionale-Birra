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
    from .models import CatalogoIngrediente, Ricetta, Cotta, ProdottoFinito
except ImportError:
    Session = Any
    CatalogoIngrediente = Any
    Ricetta = Any
    Cotta = Any
    ProdottoFinito = Any

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


def genera_prossimo_codice_prodotto_finito(db: Session) -> str:
    """Genera il prossimo codice SKU univoco per il prodotto finito a magazzino (es. PF-001)."""
    esistenti = (
        db.query(ProdottoFinito.codice)
        .filter(ProdottoFinito.codice.like("PF-%"))
        .all()
    )
    max_num = 0
    pattern = re.compile(r"^PF-(\d+)$")
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
    return f"PF-{max_num + 1:03d}"


def genera_codice_lotto_imbottigliamento(cotta, formato_ml: int = None, tipo_pkg: str = None) -> str:
    """
    Genera il codice lotto a norma di legge per il prodotto finito (D.Lgs 109/92 e Reg. UE 1169/2011).
    Esempio: L-COT-2026-001-330ML oppure L-COT-2026-001-FUSTO30L.
    """
    now = datetime.now()
    if cotta and getattr(cotta, "codice", None):
        cotta_id_str = cotta.codice
    elif cotta and getattr(cotta, "id", None):
        cotta_id_str = f"COT-{now.year}-{cotta.id:03d}"
    else:
        cotta_id_str = f"COT-{now.strftime('%Y%m')}"

    dettaglio = ""
    if formato_ml:
        if formato_ml >= 1000:
            litri = formato_ml / 1000.0
            dettaglio = f"-{litri:g}L"
        else:
            dettaglio = f"-{formato_ml}ML"
    elif tipo_pkg:
        dettaglio = f"-{tipo_pkg.upper()[:3]}"

    return f"L-{cotta_id_str}{dettaglio}"
