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
    ingredienti = relationship("IngredienteRicetta", back_populates="ricetta", cascade="all, delete-orphan")


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
