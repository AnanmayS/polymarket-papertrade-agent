from datetime import timedelta

from app.models.market import Market
from app.models.risk import RiskDecision
from app.models.signal import Signal
from app.services.execution_service import PaperExecutionService
from app.services.polymarket_client import PolymarketClient
from app.services.settlement_service import SettlementService
from app.utils.time import utc_now


def seed_trade_dependencies(db_session):
    market = Market(
        external_id="demo-trade-market",
        slug="demo-trade-market",
        question="Will the home team win?",
        category="sports",
        sports_league="MLB",
        active=True,
        closed=False,
        archived=False,
        liquidity=80_000,
        volume=120_000,
        best_bid=0.54,
        best_ask=0.56,
        last_trade_price=0.55,
        spread=0.02,
        implied_probability=0.55,
        opportunity_score=0.72,
        resolution_time=utc_now() + timedelta(hours=2),
        metadata_json={"demo_final_outcome": True},
    )
    db_session.add(market)
    db_session.flush()

    signal = Signal(
        market_id=market.id,
        mode="heuristic",
        status="candidate",
        features_json={},
        feature_importance_json={"momentum_component": 0.04},
        market_probability=0.55,
        fair_probability=0.62,
        edge=0.07,
        expected_value_proxy=0.07,
        confidence=0.81,
        opportunity_score=0.72,
        rationale="positive edge",
    )
    db_session.add(signal)
    db_session.flush()

    decision = RiskDecision(
        market_id=market.id,
        signal_id=signal.id,
        approved=True,
        reason_codes=["approved"],
        bankroll_before=10_000,
        proposed_stake=250,
        confidence=0.81,
        details_json={},
    )
    db_session.add(decision)
    db_session.commit()
    return market, signal, decision


def test_execution_applies_fees_and_slippage(db_session, test_settings) -> None:
    market, signal, decision = seed_trade_dependencies(db_session)
    trade = PaperExecutionService(db_session, test_settings).execute_trade(signal, decision, market)

    assert trade.fill_price > market.implied_probability
    assert trade.fees_paid > 0
    assert trade.slippage_paid > 0
    assert trade.quantity > 0


def test_settlement_realizes_pnl_and_creates_postmortem(db_session, test_settings) -> None:
    market, signal, decision = seed_trade_dependencies(db_session)
    execution_service = PaperExecutionService(db_session, test_settings)
    trade = execution_service.execute_trade(signal, decision, market)
    market.closed = True
    market.resolution_time = utc_now() - timedelta(minutes=5)
    db_session.commit()

    SettlementService(db_session, test_settings).settle_trade(
        trade.id, outcome_yes=True, signal=signal
    )
    db_session.commit()

    refreshed = db_session.get(type(trade), trade.id)
    assert refreshed.status == "settled"
    assert refreshed.realized_pnl != 0


def test_resolved_outcome_handles_normalized_yes_no_prices(test_settings) -> None:
    client = PolymarketClient(test_settings)

    outcome = client.extract_resolved_outcome(
        {
            "metadata_json": {
                "outcomes": ["Yes", "No"],
                "outcome_prices": ["0.9995", "0.0005"],
            }
        }
    )

    assert outcome is True


def test_resolved_outcome_handles_normalized_no_winner(test_settings) -> None:
    client = PolymarketClient(test_settings)

    outcome = client.extract_resolved_outcome(
        {
            "metadata_json": {
                "outcomes": ["Yes", "No"],
                "outcome_prices": ["0.0005", "0.9995"],
            }
        }
    )

    assert outcome is False
