"""Run one paper-trading cycle and exit."""

from __future__ import annotations

from pprint import pprint

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import build_session_factory, init_database
from app.services.engine_service import EngineService


def main() -> None:
    configure_logging()
    settings = get_settings()
    init_database(settings.active_database_url)
    session_factory = build_session_factory(settings.active_database_url)
    session = session_factory()
    try:
        result = EngineService(session, settings).run_cycle()
        pprint(
            {
                "scan": result["scan"].markets_scanned,
                "signals": result["signals"].signals_created,
                "risk": result["risk"].decisions_created,
                "trades": result["trades"].trades_created,
                "settled": result["settlement"].settled_trades,
            }
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
