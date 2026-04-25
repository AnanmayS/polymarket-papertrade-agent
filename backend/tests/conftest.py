from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import build_session_factory, init_database
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        use_live_polymarket_data=False,
        seed_demo_data=False,
        scheduler_enabled=False,
        min_liquidity=10_000,
        min_volume=5_000,
        max_spread=0.1,
        min_hours_to_resolution=1,
        max_hours_to_resolution=500,
        min_confidence=0.3,
        initial_bankroll=10_000,
        max_position_size_pct=0.05,
        max_market_exposure_pct=0.1,
        max_category_exposure_pct=0.25,
        max_open_trades=5,
    )


@pytest.fixture
def client(test_settings: Settings):
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session(test_settings: Settings):
    init_database(test_settings.active_database_url)
    session_factory = build_session_factory(test_settings.active_database_url)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
