"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "backend" / "demo.db"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(PROJECT_ROOT / ".env")),
        extra="ignore",
    )

    app_name: str = "Polymarket Paper Trading Agent"
    app_env: Literal["development", "test", "production"] = "development"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    database_url: str = f"sqlite:///{DEFAULT_SQLITE_PATH}"
    local_database_url: str = f"sqlite:///{DEFAULT_SQLITE_PATH}"
    redis_url: str = "redis://localhost:6379/0"
    use_redis: bool = False

    polymarket_gamma_url: str = "https://gamma-api.polymarket.com"
    polymarket_clob_url: str = "https://clob.polymarket.com"
    use_live_polymarket_data: bool = True
    seed_demo_data: bool = True
    market_timezone: str = "America/New_York"
    resolution_window_days: int = 7

    initial_bankroll: float = 10_000.0
    min_liquidity: float = 500.0
    min_volume: float = 2_500.0
    max_spread: float = 0.35
    min_hours_to_resolution: float = 0.25
    max_hours_to_resolution: int = 336
    min_confidence: float = 0.35
    max_position_size_pct: float = 0.03
    max_market_exposure_pct: float = 0.06
    max_category_exposure_pct: float = 0.20
    max_daily_loss_pct: float = 0.05
    max_open_trades: int = 10
    fractional_kelly: float = 0.25
    default_signal_mode: str = "heuristic"
    min_edge_to_trade: float = 0.025

    scheduler_enabled: bool = True
    auto_run_on_startup: bool = True
    scan_interval_seconds: int = 300
    signal_interval_seconds: int = 600
    trade_interval_seconds: int = 900
    settlement_interval_seconds: int = 1800
    agent_cycle_interval_seconds: int = 300

    request_timeout_seconds: float = 10.0
    scanner_limit: int = 100
    slippage_bps: int = 50
    fee_bps: int = 20
    partial_fill_ratio: float = 1.0

    demo_data_path: str = Field(default="app/data/demo_markets.json")

    @property
    def active_database_url(self) -> str:
        """Prefer DATABASE_URL when present, otherwise fall back to a local sqlite db."""

        database_url = self.database_url or self.local_database_url
        if database_url.startswith("sqlite:///./"):
            relative_path = database_url.removeprefix("sqlite:///./")
            return f"sqlite:///{PROJECT_ROOT / relative_path}"
        return database_url


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()
