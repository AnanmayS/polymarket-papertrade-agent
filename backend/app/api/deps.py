"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings


def get_db(request: Request) -> Generator[Session]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings
