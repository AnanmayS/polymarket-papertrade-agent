from datetime import datetime, timedelta

from app.models.market import Market
from app.models.trade import Trade
from app.services.engine_service import EngineService
from app.services.execution_service import ExecutionRunResult
from app.services.risk_service import RiskRunResult
from app.services.scanner_service import ScanResult
from app.services.settlement_service import SettlementRunResult
from app.services.signal_service import SignalRunResult
from app.utils.time import to_local, utc_now


def test_scan_signal_trade_and_settlement_flow(client) -> None:
    scan_response = client.post("/engine/run-scan")
    assert scan_response.status_code == 200
    assert scan_response.json()["created"] > 0

    signals_response = client.post("/engine/run-signals")
    assert signals_response.status_code == 200
    assert signals_response.json()["created"] > 0

    trade_response = client.post("/engine/run-paper-trades")
    assert trade_response.status_code == 200

    markets = client.get("/markets/active")
    assert markets.status_code == 200
    assert len(markets.json()) > 0
    for market in markets.json():
        resolution_time = to_local(
            datetime.fromisoformat(market["resolution_time"]),
            "America/New_York",
        )
        assert resolution_time is not None
        local_now = to_local(utc_now(), "America/New_York")
        assert local_now is not None
        assert resolution_time >= local_now
        assert resolution_time <= local_now + timedelta(days=7)

    signals = client.get("/signals")
    assert signals.status_code == 200
    assert len(signals.json()) > 0

    trades = client.get("/trades")
    assert trades.status_code == 200
    assert len(trades.json()) > 0

    session = client.app.state.session_factory()
    try:
        market = session.query(Market).first()
        trade = session.query(Trade).first()
        assert market is not None
        assert trade is not None
        market.closed = True
        market.resolution_time = utc_now() - timedelta(minutes=5)
        session.commit()
    finally:
        session.close()

    settlement_response = client.post("/engine/settle-paper-trades")
    assert settlement_response.status_code == 200

    postmortems = client.get("/postmortems")
    assert postmortems.status_code == 200
    assert len(postmortems.json()) >= 1


def test_run_cycle_settles_before_and_after_new_trade_work(db_session, test_settings, monkeypatch):
    calls: list[str] = []

    def settle(self):
        calls.append("settle")
        return SettlementRunResult(settled_trades=1, notes=[f"settle:{len(calls)}"])

    def scan(self):
        calls.append("scan")
        return ScanResult(markets_scanned=2, source="test")

    def signals(self, mode=None):
        calls.append("signals")
        return SignalRunResult(signals_created=1, notes=[]), RiskRunResult(
            decisions_created=1,
            notes=[],
        )

    def trades(self):
        calls.append("trades")
        return ExecutionRunResult(trades_created=1, notes=[])

    monkeypatch.setattr(EngineService, "settle_paper_trades", settle)
    monkeypatch.setattr(EngineService, "run_scan", scan)
    monkeypatch.setattr(EngineService, "run_signals", signals)
    monkeypatch.setattr(EngineService, "run_paper_trades", trades)

    result = EngineService(db_session, test_settings).run_cycle()

    assert calls == ["settle", "scan", "signals", "trades", "settle"]
    assert result["settlement"].settled_trades == 2
    assert result["trades"].trades_created == 1
