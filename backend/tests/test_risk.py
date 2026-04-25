from app.models.market import Market
from app.models.risk import RiskDecision
from app.models.signal import Signal
from app.models.trade import Position
from app.services.risk_service import RiskService


def test_position_sizing_is_capped(db_session, test_settings) -> None:
    service = RiskService(db_session, test_settings)
    signal = Signal(
        market_id=1,
        mode="heuristic",
        status="candidate",
        features_json={},
        feature_importance_json={},
        market_probability=0.52,
        fair_probability=0.6,
        edge=0.08,
        expected_value_proxy=0.08,
        confidence=0.9,
        opportunity_score=0.8,
        rationale="test",
    )
    sized = service.size_position(signal, bankroll=10_000)
    assert sized <= 500
    assert sized > 0


def test_risk_blocks_low_confidence_signal(db_session, test_settings) -> None:
    market = Market(
        external_id="mkt-1",
        slug="market-1",
        question="Will Team A win?",
        category="sports",
        sports_league="NBA",
        active=True,
        closed=False,
        archived=False,
        liquidity=50_000,
        volume=90_000,
        best_bid=0.49,
        best_ask=0.51,
        last_trade_price=0.5,
        spread=0.02,
        implied_probability=0.5,
        opportunity_score=0.7,
        metadata_json={},
    )
    db_session.add(market)
    db_session.flush()

    signal = Signal(
        market_id=market.id,
        mode="heuristic",
        status="candidate",
        features_json={},
        feature_importance_json={},
        market_probability=0.5,
        fair_probability=0.52,
        edge=0.02,
        expected_value_proxy=0.02,
        confidence=0.2,
        opportunity_score=0.4,
        rationale="low confidence",
    )
    db_session.add(signal)
    db_session.commit()

    decision = RiskService(db_session, test_settings).evaluate_signal(signal, market)
    assert decision.approved is False
    assert "confidence_below_threshold" in decision.reason_codes


def test_risk_respects_max_open_trades_across_batch(db_session, test_settings) -> None:
    service = RiskService(db_session, test_settings)

    for index in range(test_settings.max_open_trades):
        market = Market(
            external_id=f"open-{index}",
            slug=f"open-{index}",
            question=f"Existing open market {index}",
            category="sports",
            sports_league="NBA",
            active=True,
            closed=False,
            archived=False,
            liquidity=50_000,
            volume=90_000,
            best_bid=0.49,
            best_ask=0.51,
            last_trade_price=0.5,
            spread=0.02,
            implied_probability=0.5,
            opportunity_score=0.7,
            metadata_json={},
        )
        db_session.add(market)
        db_session.flush()
        db_session.add(
            Position(
                market_id=market.id,
                side="buy_yes",
                status="open",
                quantity=10,
                avg_price=0.5,
                cost_basis=100,
                market_price=0.5,
                realized_pnl=0.0,
                unrealized_pnl=0.0,
                metadata_json={},
            )
        )

    candidate_market = Market(
        external_id="candidate-1",
        slug="candidate-1",
        question="Will Team B win?",
        category="sports",
        sports_league="NBA",
        active=True,
        closed=False,
        archived=False,
        liquidity=50_000,
        volume=90_000,
        best_bid=0.49,
        best_ask=0.51,
        last_trade_price=0.5,
        spread=0.02,
        implied_probability=0.5,
        opportunity_score=0.7,
        metadata_json={},
    )
    db_session.add(candidate_market)
    db_session.flush()
    signal = Signal(
        market_id=candidate_market.id,
        mode="heuristic",
        status="candidate",
        features_json={},
        feature_importance_json={},
        market_probability=0.5,
        fair_probability=0.62,
        edge=0.12,
        expected_value_proxy=0.12,
        confidence=0.9,
        opportunity_score=0.8,
        rationale="should be blocked by open trade cap",
    )
    db_session.add(signal)
    db_session.commit()

    decision = service.evaluate_signal(signal, candidate_market)
    assert decision.approved is False
    assert "max_open_trades_reached" in decision.reason_codes


def test_risk_tracks_market_exposure_across_batch(db_session, test_settings) -> None:
    market = Market(
        external_id="same-market",
        slug="same-market",
        question="Will Team C win?",
        category="sports",
        sports_league="NBA",
        active=True,
        closed=False,
        archived=False,
        liquidity=50_000,
        volume=90_000,
        best_bid=0.49,
        best_ask=0.51,
        last_trade_price=0.5,
        spread=0.02,
        implied_probability=0.5,
        opportunity_score=0.8,
        metadata_json={},
    )
    db_session.add(market)
    db_session.flush()

    signals: list[Signal] = []
    for index in range(3):
        signal = Signal(
            market_id=market.id,
            mode="heuristic",
            status="candidate",
            features_json={},
            feature_importance_json={},
            market_probability=0.5,
            fair_probability=0.62,
            edge=0.12,
            expected_value_proxy=0.12,
            confidence=0.9,
            opportunity_score=0.8 - (index * 0.01),
            rationale=f"batch signal {index}",
        )
        db_session.add(signal)
        signals.append(signal)
    db_session.commit()

    service = RiskService(db_session, test_settings)
    result = service.evaluate_signals()
    assert result.decisions_created == 3

    decisions = (
        db_session.query(RiskDecision)
        .filter(RiskDecision.market_id == market.id)
        .order_by(RiskDecision.id.asc())
        .all()
    )
    assert len(decisions) == 3
    assert decisions[0].approved is True
    assert decisions[1].approved is True
    assert decisions[2].approved is False
    assert "market_exposure_cap_exceeded" in decisions[2].reason_codes
