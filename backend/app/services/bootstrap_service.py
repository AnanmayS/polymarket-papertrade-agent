"""Bootstrap helpers for demo data and scheduled portfolio snapshots."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.services.engine_service import EngineService


class BootstrapService:
    """Seed initial data when the database is empty."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def ensure_seeded(self) -> None:
        market_count = self.session.scalar(select(func.count()).select_from(Market)) or 0
        if market_count == 0 and self.settings.seed_demo_data:
            EngineService(self.session, self.settings).run_cycle()
        elif self.settings.auto_run_on_startup:
            EngineService(self.session, self.settings).run_cycle()
