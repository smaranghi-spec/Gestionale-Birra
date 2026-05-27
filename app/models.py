from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base


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

    stile = relationship("Stile", back_populates="ricette")
    ingredienti = relationship(
        "IngredienteRicetta", back_populates="ricetta", cascade="all, delete-orphan"
    )

    cotte = relationship("Cotta", back_populates="ricetta")
    profilo_acqua = relationship(
        "ProfiloAcqua",
        back_populates="ricetta",
        uselist=False,
        cascade="all, delete-orphan",
    )
    profilo_mash = relationship(
        "ProfiloAmmostamento",
        back_populates="ricetta",
        uselist=False,
        cascade="all, delete-orphan",
    )


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
    """Profilo chimico dell'acqua di processo per una ricetta."""

    __tablename__ = "profilo_acqua"

    id = Column(Integer, primary_key=True, index=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), unique=True, nullable=False)
    nome = Column(String, default="Custom")
    ca = Column(Float, default=0.0)  # Calcio mg/L
    mg = Column(Float, default=0.0)  # Magnesio mg/L
    na = Column(Float, default=0.0)  # Sodio mg/L
    cl = Column(Float, default=0.0)  # Cloruri mg/L
    so4 = Column(Float, default=0.0)  # Solfati mg/L
    hco3 = Column(Float, default=0.0)  # Bicarbonati mg/L

    ricetta = relationship("Ricetta", back_populates="profilo_acqua")


class ProfiloAmmostamento(Base):
    """Profilo di ammostamento con step multipli per una ricetta."""

    __tablename__ = "profilo_ammostamento"

    id = Column(Integer, primary_key=True, index=True)
    ricetta_id = Column(Integer, ForeignKey("ricette.id"), unique=True, nullable=False)
    nome = Column(String, default="Singolo infuso")
    steps_json = Column(Text, default="[]")

    ricetta = relationship("Ricetta", back_populates="profilo_mash")


# ── TRACKER DI PROCESSO ──────────────────────────────────────────────────────

STATI_COTTA = [
    "pianificata",
    "brewday",
    "fermentazione",
    "secondaria",
    "condizionamento",
    "imbottigliamento",
    "maturazione",
    "pronta",
    "archiviata",
]


class Cotta(Base):
    """Singolo lotto di produzione."""

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
    log = relationship(
        "LogCotta",
        back_populates="cotta",
        cascade="all, delete-orphan",
        order_by="LogCotta.timestamp",
    )


class LogCotta(Base):
    """Evento/misurazione nel diario di cotta."""

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
