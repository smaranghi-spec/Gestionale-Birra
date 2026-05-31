from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from .db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Attrezzatura(Base):
    __tablename__ = "attrezzature"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False, default="generico")
    descrizione = Column(Text)
    capacita_litri = Column(Float)
    ubicazione = Column(String)
    attiva = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Ricetta(Base):
    __tablename__ = "ricette"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False, unique=True)
    stile = Column(String)
    descrizione = Column(Text)
    volume_target_l = Column(Float, default=0)
    efficienza = Column(Float, default=0)
    is_pubblica = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
