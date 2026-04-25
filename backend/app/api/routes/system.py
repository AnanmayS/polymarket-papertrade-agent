"""System routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.schemas.engine import HealthResponse, SettingsRead

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_app_settings), db: Session = Depends(get_db)
) -> HealthResponse:
    db.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
        database_backend=settings.database_backend,
        scheduler_enabled=settings.scheduler_enabled,
        auto_run_on_startup=settings.auto_run_on_startup,
        paper_trading_only=True,
    )


@router.get("/settings", response_model=SettingsRead)
def get_settings_snapshot(settings: Settings = Depends(get_app_settings)) -> SettingsRead:
    return SettingsRead(
        initial_bankroll=settings.initial_bankroll,
        min_liquidity=settings.min_liquidity,
        min_volume=settings.min_volume,
        max_spread=settings.max_spread,
        min_confidence=settings.min_confidence,
        max_position_size_pct=settings.max_position_size_pct,
        max_market_exposure_pct=settings.max_market_exposure_pct,
        max_category_exposure_pct=settings.max_category_exposure_pct,
        max_daily_loss_pct=settings.max_daily_loss_pct,
        max_open_trades=settings.max_open_trades,
        fractional_kelly=settings.fractional_kelly,
        default_signal_mode=settings.default_signal_mode,
    )
