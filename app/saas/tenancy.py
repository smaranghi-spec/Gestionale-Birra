"""
Multi-tenancy trasparente a livello ORM.

- Ogni tabella "di birrificio" riceve una colonna `tenant_id` (aggiunta in modo additivo).
- Ogni SELECT/UPDATE/DELETE ORM viene filtrato automaticamente sul tenant della richiesta.
- Ogni INSERT riceve automaticamente il `tenant_id` della richiesta.
- Tabelle "condivise" (stili, catalogo, preset acqua): i record globali (tenant_id NULL) sono
  visibili a tutti in sola lettura; ogni birrificio può aggiungere i propri record privati.

I dati esistenti vengono assegnati al tenant piattaforma (id=1, Podere Castelvieto) senza
alcuna perdita o modifica dei valori.
"""
import contextvars
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, Text, event, or_, text
from sqlalchemy.orm import Session, with_loader_criteria

from ..db import Base, engine

PLATFORM_TENANT_ID = 1
FREE_MAX_RICETTE = 3

PIANI = {
    "free": {"nome": "Free", "prezzo": "0 €", "periodo": "per sempre", "livello": 0},
    "pro": {"nome": "Pro", "prezzo": "14,90 €", "periodo": "/anno IVA inclusa", "livello": 1},
    "b2b": {"nome": "B2B Microbirrificio", "prezzo": "29,00 €", "periodo": "/mese IVA inclusa", "livello": 2},
}

# Tabelle senza isolamento (globali di piattaforma)
GLOBAL_TABLES = {"tenants", "prezzi_cache", "impostazioni"}
# Tabelle condivise: record globali (NULL) in sola lettura + record privati per tenant
OVERLAY_TABLES = {"stili", "catalogo_ingredienti", "profilo_acqua_preset"}


# ── MODELLO TENANT ────────────────────────────────────────────────────────────

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=True)
    piano = Column(String, default="free")                 # free / pro / b2b
    stato_abbonamento = Column(String, default="free")     # free / active / trialing / past_due / canceled / lifetime
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    scadenza = Column(String, nullable=True)
    iot_token = Column(String, nullable=True)
    consenso_termini_at = Column(String, nullable=True)
    consenso_versione = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))


# ── CONTESTO RICHIESTA ────────────────────────────────────────────────────────

@dataclass
class TenantCtx:
    id: int
    piano: str = "free"

    @property
    def is_platform(self) -> bool:
        return self.id == PLATFORM_TENANT_ID

    @property
    def livello(self) -> int:
        if self.is_platform:
            return 99
        return PIANI.get(self.piano, PIANI["free"])["livello"]


_current: contextvars.ContextVar[Optional[TenantCtx]] = contextvars.ContextVar("tenant_ctx", default=None)


def get_current() -> Optional[TenantCtx]:
    return _current.get()


def set_current(ctx: Optional[TenantCtx]):
    return _current.set(ctx)


def reset_current(token):
    _current.reset(token)


@contextmanager
def system_context():
    """Disabilita temporaneamente il filtro tenant (operazioni di sistema)."""
    tok = _current.set(None)
    try:
        yield
    finally:
        _current.reset(tok)


class PaywallLimit(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


class TenantWriteForbidden(Exception):
    pass


# ── INSTALLAZIONE ─────────────────────────────────────────────────────────────

_SCOPED: list = []
_OVERLAY: list = []
_installed = False


def _classify_models():
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        tname = getattr(cls, "__tablename__", None)
        if not tname or tname in GLOBAL_TABLES:
            continue
        table = cls.__table__
        if "tenant_id" not in table.c:
            col = Column("tenant_id", Integer, nullable=True, index=True)
            table.append_column(col)
            mapper.add_property("tenant_id", table.c.tenant_id)
        (_OVERLAY if tname in OVERLAY_TABLES else _SCOPED).append(cls)


def install():
    """Da chiamare all'avvio PRIMA di create_all."""
    global _installed
    if _installed:
        return
    from .. import models  # noqa: F401  (assicura che tutti i modelli siano registrati)
    _classify_models()

    @event.listens_for(Session, "do_orm_execute")
    def _add_tenant_criteria(state):
        ctx = _current.get()
        if ctx is None:
            return
        if not (state.is_select or state.is_update or state.is_delete):
            return
        if state.is_select and (state.is_column_load or state.is_relationship_load):
            return
        tid = ctx.id
        opts = []
        for cls in _SCOPED:
            opts.append(with_loader_criteria(cls, lambda c: c.tenant_id == tid,
                                             include_aliases=True, track_closure_variables=True))
        for cls in _OVERLAY:
            opts.append(with_loader_criteria(cls, lambda c: or_(c.tenant_id == tid, c.tenant_id.is_(None)),
                                             include_aliases=True, track_closure_variables=True))
        state.statement = state.statement.options(*opts)

    @event.listens_for(Session, "before_flush")
    def _assign_tenant(session, flush_context, instances):
        ctx = _current.get()
        if ctx is None:
            return
        from ..models import Ricetta
        nuove_ricette = 0
        for obj in session.new:
            if hasattr(obj, "tenant_id") and type(obj).__tablename__ not in GLOBAL_TABLES:
                if getattr(obj, "tenant_id", None) is None:
                    obj.tenant_id = ctx.id
            if isinstance(obj, Ricetta):
                nuove_ricette += 1
        # Protezione record globali condivisi (solo la piattaforma può modificarli)
        if not ctx.is_platform:
            for obj in list(session.dirty) + list(session.deleted):
                if type(obj) in _OVERLAY and getattr(obj, "tenant_id", None) is None:
                    if obj in session.deleted or session.is_modified(obj):
                        raise TenantWriteForbidden(type(obj).__tablename__)
        # Paywall: piano Free max N ricette
        if nuove_ricette and ctx.livello < 1:
            with session.no_autoflush:
                esistenti = session.query(Ricetta).count()
            if esistenti + nuove_ricette > FREE_MAX_RICETTE:
                raise PaywallLimit("ricette")

    _installed = True


# ── MIGRAZIONE ADDITIVA ───────────────────────────────────────────────────────

def migrate():
    """Aggiunge tenant_id alle tabelle esistenti e assegna i dati storici al tenant piattaforma."""
    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(engine)
    is_pg = engine.dialect.name == "postgresql"
    with engine.connect() as conn:
        for cls in _SCOPED + _OVERLAY:
            t = cls.__tablename__
            try:
                if not inspector.has_table(t):
                    continue
                cols = [c["name"] for c in inspector.get_columns(t)]
                if "tenant_id" not in cols:
                    conn.execute(text(f'ALTER TABLE "{t}" ADD COLUMN tenant_id INTEGER'))
                    conn.commit()
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS ix_{t}_tenant_id ON "{t}" (tenant_id)'))
                conn.commit()
                if cls in _SCOPED:
                    conn.execute(text(f'UPDATE "{t}" SET tenant_id = {PLATFORM_TENANT_ID} WHERE tenant_id IS NULL'))
                    conn.commit()
            except Exception as e:  # pragma: no cover
                conn.rollback()
                print(f"[saas.migrate] {t}: {e}", flush=True)

        # Tenant piattaforma (dati storici)
        try:
            row = conn.execute(text("SELECT id FROM tenants WHERE id = :i"), {"i": PLATFORM_TENANT_ID}).first()
            if not row:
                conn.execute(text(
                    "INSERT INTO tenants (id, nome, piano, stato_abbonamento, iot_token, created_at) "
                    "VALUES (:i, :n, 'b2b', 'lifetime', :tok, :c)"),
                    {"i": PLATFORM_TENANT_ID, "n": "Podere Castelvieto", "tok": secrets.token_urlsafe(18),
                     "c": datetime.now().strftime("%Y-%m-%d %H:%M")})
                conn.commit()
            if is_pg:
                conn.execute(text(
                    "SELECT setval(pg_get_serial_sequence('tenants','id'), (SELECT MAX(id) FROM tenants))"))
                conn.commit()
                for stmt in ('ALTER TABLE public."tenants" ENABLE ROW LEVEL SECURITY',
                             'REVOKE ALL ON TABLE public."tenants" FROM anon, authenticated'):
                    try:
                        conn.execute(text(stmt))
                        conn.commit()
                    except Exception:
                        conn.rollback()
        except Exception as e:  # pragma: no cover
            conn.rollback()
            print(f"[saas.migrate] tenants: {e}", flush=True)
