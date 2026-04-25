"""Database engine and session helpers."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import models  # noqa: F401
from app.db.base import Base


def build_engine(database_url: str):
    """Create a SQLAlchemy engine with sqlite-friendly defaults."""

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a scoped session factory for the active database."""

    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_database(database_url: str) -> None:
    """Create tables for the MVP schema."""

    engine = build_engine(database_url)
    Base.metadata.create_all(bind=engine)
