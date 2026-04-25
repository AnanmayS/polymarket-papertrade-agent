"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from secrets import compare_digest

from fastapi import Header, HTTPException, Request, status
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


def require_engine_control(
    request: Request,
    authorization: str | None = Header(default=None),
    x_engine_token: str | None = Header(default=None),
) -> None:
    """Require a control token for engine mutation endpoints in public deployments."""

    settings = get_app_settings(request)
    if not settings.engine_auth_enabled:
        return

    token = (x_engine_token or "").strip()
    if not token and authorization:
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = credentials.strip()

    if not token or not settings.engine_control_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing engine control token",
        )
    if not compare_digest(token, settings.engine_control_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid engine control token",
        )
