"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.engine import router as engine_router
from app.api.routes.markets import router as markets_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.postmortems import router as postmortems_router
from app.api.routes.signals import router as signals_router
from app.api.routes.system import router as system_router
from app.api.routes.trades import router as trades_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import build_session_factory, init_database
from app.services.bootstrap_service import BootstrapService
from app.services.engine_service import EngineService


def create_scheduler(app: FastAPI, settings: Settings) -> BackgroundScheduler | None:
    """Optionally start periodic background jobs for local automation."""

    if not settings.scheduler_enabled:
        return None

    scheduler = BackgroundScheduler(timezone="UTC")

    def _run_cycle() -> None:
        session = app.state.session_factory()
        try:
            EngineService(session, settings).run_cycle()
        finally:
            session.close()

    scheduler.add_job(
        _run_cycle,
        "interval",
        seconds=settings.agent_cycle_interval_seconds,
        id="agent-cycle",
    )
    scheduler.start()
    return scheduler


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI app and attach db state."""

    configure_logging()
    active_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_database(active_settings.active_database_url)
        app.state.settings = active_settings
        app.state.session_factory = build_session_factory(active_settings.active_database_url)
        session = app.state.session_factory()
        try:
            BootstrapService(session, active_settings).ensure_seeded()
            session.commit()
        finally:
            session.close()

        scheduler = create_scheduler(app, active_settings)
        try:
            yield
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)

    app = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        description=(
            "Paper-trading app for researching sports prediction markets. "
            "No wallet signing or real-money execution is performed."
        ),
        lifespan=lifespan,
    )
    allow_origins = active_settings.parsed_cors_allowed_origins or ["http://localhost:5173"]
    allow_credentials = "*" not in allow_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system_router)
    app.include_router(markets_router)
    app.include_router(signals_router)
    app.include_router(portfolio_router)
    app.include_router(trades_router)
    app.include_router(postmortems_router)
    app.include_router(engine_router)
    return app


app = create_app()
