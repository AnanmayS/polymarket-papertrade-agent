"""Seed sample markets and run the full paper-trading engine once."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.session import build_session_factory, init_database
from app.services.bootstrap_service import BootstrapService
from app.services.engine_service import EngineService


def main() -> None:
    settings = get_settings()
    init_database(settings.active_database_url)
    session_factory = build_session_factory(settings.active_database_url)
    session = session_factory()
    try:
        BootstrapService(session, settings).ensure_seeded()
        EngineService(session, settings).run_scan()
        EngineService(session, settings).run_signals()
        EngineService(session, settings).run_paper_trades()
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    main()
