"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
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
    cors_allowed_origins: str = "http://localhost:5173"
    engine_control_token: str | None = None

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

    scheduler_enabled: bool = False
    auto_run_on_startup: bool = False
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

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        """Reject unsafe production defaults."""

        if self.app_env != "production":
            return self

        if not self.engine_control_token:
            raise ValueError("ENGINE_CONTROL_TOKEN is required when APP_ENV=production")
        if self.scheduler_enabled:
            raise ValueError(
                "SCHEDULER_ENABLED must be false in production; use an external scheduler"
            )
        if self.auto_run_on_startup:
            raise ValueError(
                "AUTO_RUN_ON_STARTUP must be false in production; trigger cycles explicitly"
            )
        return self

    @property
    def active_database_url(self) -> str:
        """Prefer DATABASE_URL when present, otherwise fall back to a local sqlite db."""

        database_url = self.database_url or self.local_database_url
        if database_url.startswith("sqlite:///./"):
            relative_path = database_url.removeprefix("sqlite:///./")
            return f"sqlite:///{PROJECT_ROOT / relative_path}"
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if database_url.startswith("postgresql://") and "+" not in database_url.partition("://")[0]:
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url

    @property
    def database_backend(self) -> str:
        """Expose only the database backend name for health reporting."""

        parsed = urlparse(self.active_database_url)
        scheme = parsed.scheme or "unknown"
        return scheme.split("+", maxsplit=1)[0]

    @property
    def parsed_cors_allowed_origins(self) -> list[str]:
        """Return configured CORS origins from a CSV env var."""

        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def engine_auth_enabled(self) -> bool:
        """Protect control endpoints in production or when a token is configured."""

        return self.app_env == "production" or bool(self.engine_control_token)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()
