import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from .db import Base


# ── AUTH ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nome = Column(String, default="")
    ruolo = Column(String, default="birraio")   # admin / birraio
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    @staticmethod
    def hash_pw(plain: str) -> str:
        return hashlib.sha256(plain.encode()).hexdigest()

    def check_pw(self, plain: str) -> bool:
        return self.password_hash == hashlib.sha256(plain.encode()).hexdigest()


# ── STILI BJCP ────────────────────────────────────────────────────────────────

class Stile(Base):
    __tablename__ = "stili"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    linea_guida = Column(String, default="")
    og_min = Column(Float, nullable=True)
    og_max = Column(Float, nullable=True)
    fg_min = Column(Float, nullable=True)
    fg_max = Column(Float, nullable=True)
    ibu_min = Column(Float, nullable=True)
    ibu_max = Column(Float, nullable=True)
    srm_min = Column(Float, nullable=True)
    srm_max = Column(Float, nullable=True)
    ebc_min = Column(Float, nullable=True)
    ebc_max = Column(Float, nullable=True)
    abv_min = Column(Float, nullable=True)
    abv_max = Column(Float, nullable=True)
    ricette = relationship("Ricetta", back_populates="stile")


# ── RICETTE ───────────────────────────────────────────────────────────────────

class Ricetta(Base):
    __tablename__ = "ricette"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, default="All Grain")
    volume_target_litri = Column(Float, default=20.0)
    efficienza = Column(Float, default=75.0)
    versione = Column(Integer, default=1)
    note = Column(Text, nullable=True)
    stile_id = Column(Integer, ForeignKey("stili.id"), nullable=True)
    pubblica = Column(Boolean, default=False)
    stile = relationship("Stile", back_populates="ricette")
    ingredienti = relationship("IngredienteRicetta", back_populates="ricetta", cascade="all, delete-orphan")
    cotte = relationship("Cotta", back_populates="ricetta")
    profilo_acqua = relationship("ProfiloAcqua", back_populates="ricetta", uselist=False, cascade="all, delete-orphan")
    profilo_mash = relationship("ProfiloAmmostamento", back_populates="ricetta", uselist=False, cascade="all, delete-orphan")


class IngredienteRicetta(Base):
    __tablename__ = "ingredienti_ricetta"
    id = Column(Integer, primary_key=True, index=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), nullable=False)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    quantita = Column(Float, default=0.0)
    unita = Column(String, default="kg")
    note = Column(Text, nullable=True)
    time_min = Column(Integer, nullable=True)
    prezzo_unitario = Column(Float, nullable=True)
    fermentable_type = Column(String, nullable=True)
    yield_percent = Column(Float, nullable=True)
    color_srm = Column(Float, nullable=True)
    alpha_acid = Column(Float, nullable=True)
    hop_use = Column(String, nullable=True)
    hop_form = Column(String, nullable=True)
    attenuation = Column(Float, nullable=True)
    yeast_type = Column(String, nullable=True)
    yeast_form = Column(String, nullable=True)
    misc_type = Column(String, nullable=True)
    misc_use = Column(String, nullable=True)
    ricetta = relationship("Ricetta", back_populates="ingredienti")


class CatalogoIngrediente(Base):
    __tablename__ = "catalogo_ingredienti"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    fermentable_type = Column(String, nullable=True)
    yield_percent = Column(Float, nullable=True)
    color_srm = Column(Float, nullable=True)
    alpha_acid = Column(Float, nullable=True)
    hop_use = Column(String, nullable=True)
    hop_form = Column(String, nullable=True)
    attenuation = Column(Float, nullable=True)
    yeast_type = Column(String, nullable=True)
    yeast_form = Column(String, nullable=True)
    misc_type = Column(String, nullable=True)
    misc_use = Column(String, nullable=True)


class ProfiloAcqua(Base):
    __tablename__ = "profilo_acqua"
    id = Column(Integer, primary_key=True, index=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), unique=True, nullable=False)
    nome = Column(String, default="Custom")
    ca = Column(Float, default=0.0)
    mg = Column(Float, default=0.0)
    na = Column(Float, default=0.0)
    cl = Column(Float, default=0.0)
    so4 = Column(Float, default=0.0)
    hco3 = Column(Float, default=0.0)
    ricetta = relationship("Ricetta", back_populates="profilo_acqua")


class ProfiloAmmostamento(Base):
    __tablename__ = "profilo_ammostamento"
    id = Column(Integer, primary_key=True, index=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), unique=True, nullable=False)
    nome = Column(String, default="Singolo infuso")
    steps_json = Column(Text, default="[]")
    ricetta = relationship("Ricetta", back_populates="profilo_mash")


# ── COTTE ─────────────────────────────────────────────────────────────────────

STATI_COTTA = [
    "pianificata", "brewday", "fermentazione", "secondaria",
    "condizionamento", "imbottigliamento", "maturazione", "pronta", "archiviata",
]


class Cotta(Base):
    __tablename__ = "cotte"
    id = Column(Integer, primary_key=True, index=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), nullable=True)
    nome = Column(String, nullable=False)
    codice = Column(String, nullable=True)
    stato = Column(String, default="pianificata")
    data_brew = Column(String, nullable=True)
    volume_pre_bollitura = Column(Float, nullable=True)
    volume_post_bollitura = Column(Float, nullable=True)
    ph_mash = Column(Float, nullable=True)
    ph_pre_bollitura = Column(Float, nullable=True)
    temp_mash_gradi = Column(Float, nullable=True)
    durata_bollitura_min = Column(Integer, nullable=True)
    efficienza_reale = Column(Float, nullable=True)
    fermentatore = Column(String, nullable=True)
    data_inoculo = Column(String, nullable=True)
    temp_fermentazione = Column(Float, nullable=True)
    og_reale = Column(Float, nullable=True)
    data_travasamento = Column(String, nullable=True)
    temp_secondaria = Column(Float, nullable=True)
    data_imbottigliamento = Column(String, nullable=True)
    tipo_packaging = Column(String, nullable=True)
    volume_imbottigliato = Column(Float, nullable=True)
    carbonatazione_vols = Column(Float, nullable=True)
    priming_sugar_g = Column(Float, nullable=True)
    fg_reale = Column(Float, nullable=True)
    abv_reale = Column(Float, nullable=True)
    colore_visivo = Column(String, nullable=True)
    limpidezza = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    ricetta = relationship("Ricetta", back_populates="cotte")
    log = relationship("LogCotta", back_populates="cotta", cascade="all, delete-orphan", order_by="LogCotta.timestamp")
    degustazioni = relationship("Degustazione", back_populates="cotta", cascade="all, delete-orphan")


class LogCotta(Base):
    __tablename__ = "log_cotta"
    id = Column(Integer, primary_key=True, index=True)
    cotta_id = Column(Integer, ForeignKey("cotte.id"), nullable=False)
    timestamp = Column(String, nullable=False)
    fase = Column(String, nullable=True)
    tipo = Column(String, nullable=False, default="nota")
    descrizione = Column(String, nullable=False)
    valore = Column(Float, nullable=True)
    unita = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    cotta = relationship("Cotta", back_populates="log")


class Degustazione(Base):
    __tablename__ = "degustazioni"
    id = Column(Integer, primary_key=True, index=True)
    cotta_id = Column(Integer, ForeignKey("cotte.id"), nullable=False)
    data = Column(String, nullable=False)
    degustatore = Column(String, nullable=True)
    aspetto = Column(Text, nullable=True)
    aroma = Column(Text, nullable=True)
    gusto = Column(Text, nullable=True)
    sensazione = Column(Text, nullable=True)
    voto = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    cotta = relationship("Cotta", back_populates="degustazioni")


# ── ATTREZZATURA ──────────────────────────────────────────────────────────────

class Attrezzatura(Base):
    __tablename__ = "attrezzature"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, default="generico")
    marca = Column(String, nullable=True)
    modello = Column(String, nullable=True)
    numero_seriale = Column(String, nullable=True)
    capacita_litri = Column(Float, nullable=True)
    ubicazione = Column(String, nullable=True)
    data_acquisto = Column(String, nullable=True)
    ultima_manutenzione = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    attiva = Column(Boolean, default=True)


# ── INVENTARIO ────────────────────────────────────────────────────────────────

class InventarioItem(Base):
    __tablename__ = "inventario"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    categoria = Column(String, default="consumabile")  # consumabile / non_consumabile
    unita = Column(String, default="pz")
    quantita = Column(Float, default=0.0)
    quantita_minima = Column(Float, default=0.0)
    prezzo_unitario = Column(Float, nullable=True)
    fornitore = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    ultimo_aggiornamento = Column(String, nullable=True)


# ── VENDITE ───────────────────────────────────────────────────────────────────

class Vendita(Base):
    __tablename__ = "vendite"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(String, nullable=False)
    cliente = Column(String, nullable=True)
    prodotto = Column(String, nullable=False)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), nullable=True)
    quantita_litri = Column(Float, nullable=True)
    n_bottiglie = Column(Integer, nullable=True)
    prezzo_euro = Column(Float, nullable=True)
    note = Column(Text, nullable=True)


# ── CALENDARIO / PRESENZE ─────────────────────────────────────────────────────

class EventoCalendario(Base):
    __tablename__ = "eventi_calendario"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(String, nullable=False)
    ora = Column(String, nullable=True)
    tipo = Column(String, default="altro")  # cotta / imbottigliamento / pulizia / degustazione / altro
    titolo = Column(String, nullable=False)
    descrizione = Column(Text, nullable=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), nullable=True)
    responsabile = Column(String, nullable=True)
    completato = Column(Boolean, default=False)


class Presenza(Base):
    __tablename__ = "presenze"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(String, nullable=False)
    utente_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    utente_nome = Column(String, nullable=False)
    check_in = Column(String, nullable=True)
    check_out = Column(String, nullable=True)
    ore_totali = Column(Float, nullable=True)
    note = Column(Text, nullable=True)


# ── REGISTRO PULIZIE ──────────────────────────────────────────────────────────

class RegistroPulizie(Base):
    __tablename__ = "registro_pulizie"
    id = Column(Integer, primary_key=True, index=True)
    data = Column(String, nullable=False)
    tipo_pulizia = Column(String, nullable=False)
    luogo = Column(String, nullable=False)
    operatore = Column(String, nullable=True)
    detergente = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
