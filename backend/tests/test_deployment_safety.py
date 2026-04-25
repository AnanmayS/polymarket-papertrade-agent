from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_production_requires_engine_control_token() -> None:
    with pytest.raises(ValueError, match="ENGINE_CONTROL_TOKEN"):
        Settings(
            app_env="production",
            scheduler_enabled=False,
            auto_run_on_startup=False,
        )


def test_engine_routes_require_token_in_production(tmp_path: Path) -> None:
    token = tmp_path.name
    settings = Settings(
        app_env="production",
        database_url=f"sqlite:///{tmp_path / 'prod.db'}",
        use_live_polymarket_data=False,
        seed_demo_data=False,
        scheduler_enabled=False,
        auto_run_on_startup=False,
        engine_control_token=token,
    )

    app = create_app(settings)
    with TestClient(app) as client:
        unauthorized = client.post("/engine/run-cycle")
        assert unauthorized.status_code == 401

        authorized = client.post(
            "/engine/run-cycle",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert authorized.status_code == 200


def test_health_hides_database_url(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert "database_url" not in payload
    assert payload["database_backend"] == "sqlite"
