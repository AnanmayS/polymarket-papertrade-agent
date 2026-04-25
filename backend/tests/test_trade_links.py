from app.models.market import Market
from app.models.trade import Trade
from app.services.polymarket_client import PolymarketClient


def _create_market(db_session, **overrides) -> Market:
    market = Market(
        external_id=overrides.get("external_id", "1793283"),
        slug=overrides.get("slug", "tur-gal-fen-2026-04-26-gal"),
        question=overrides.get("question", "Will Galatasaray SK win on 2026-04-26?"),
        category="sports",
        subcategory="Soccer",
        sports_league="Super Lig",
        event_title="Galatasaray SK vs. Fenerbahce SK",
        outcome_name="YES",
        active=True,
        closed=False,
        archived=False,
        liquidity=150000.0,
        volume=5000.0,
        best_bid=0.42,
        best_ask=0.43,
        last_trade_price=0.43,
        spread=0.01,
        implied_probability=0.425,
        opportunity_score=0.8,
        resolution_time=None,
        metadata_json=overrides.get("metadata_json", {"sports_market_type": "moneyline"}),
    )
    db_session.add(market)
    db_session.flush()
    return market


def _create_trade(db_session, market_id: int) -> Trade:
    trade = Trade(
        market_id=market_id,
        side="buy_yes",
        status="opened",
        stake=100.0,
        quantity=200.0,
        fill_price=0.5,
        fees_paid=0.2,
        slippage_paid=0.4,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        confidence=0.9,
        entry_edge=0.04,
        rationale="test trade",
        metadata_json={},
    )
    db_session.add(trade)
    db_session.commit()
    db_session.refresh(trade)
    return trade


def test_trades_backfill_live_event_slug(client, db_session, monkeypatch):
    market = _create_market(db_session)
    _create_trade(db_session, market.id)

    monkeypatch.setattr(
        PolymarketClient,
        "fetch_active_event_slug_map",
        lambda self: {"1793283": "tur-gal-fen-2026-04-26"},
    )

    response = client.get("/trades")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["market_url"] == "https://polymarket.com/event/tur-gal-fen-2026-04-26"

    db_session.refresh(market)
    assert market.metadata_json["event_slug"] == "tur-gal-fen-2026-04-26"


def test_trades_hide_unconfirmed_moneyline_links(client, db_session, monkeypatch):
    market = _create_market(db_session, external_id="1762763", slug="tur-iba-kas-2026-04-24-iba")
    _create_trade(db_session, market.id)

    monkeypatch.setattr(
        PolymarketClient,
        "fetch_active_event_slug_map",
        lambda self: {},
    )

    response = client.get("/trades")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["market_url"] is None
