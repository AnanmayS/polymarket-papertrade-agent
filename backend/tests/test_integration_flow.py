from datetime import datetime, timedelta

from app.models.market import Market
from app.models.trade import Trade
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
