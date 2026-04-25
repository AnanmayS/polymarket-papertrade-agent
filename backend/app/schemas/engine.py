"""Engine action schemas."""

from pydantic import BaseModel


class EngineActionResponse(BaseModel):
    message: str
    created: int
    notes: list[str] = []


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    database_backend: str
    scheduler_enabled: bool
    auto_run_on_startup: bool
    paper_trading_only: bool


class SettingsRead(BaseModel):
    initial_bankroll: float
    min_liquidity: float
    min_volume: float
    max_spread: float
    min_confidence: float
    max_position_size_pct: float
    max_market_exposure_pct: float
    max_category_exposure_pct: float
    max_daily_loss_pct: float
    max_open_trades: int
    fractional_kelly: float
    default_signal_mode: str
