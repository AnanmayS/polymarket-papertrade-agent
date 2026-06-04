from datetime import timedelta

from app.models.market import Market
from app.models.signal import Signal
from app.models.trade import Trade
from app.services.sentiment_service import SentimentService
from app.services.signal_service import SignalService
from app.services.strategy_evaluation_service import StrategyEvaluationService
from app.utils.time import utc_now


def _market(db_session, **overrides) -> Market:
    market = Market(
        external_id=overrides.get("external_id", "sentiment-market"),
        slug=overrides.get("slug", "sentiment-market"),
        question=overrides.get("question", "Will Team G win?"),
        category="sports",
        sports_league="NBA",
        event_title="Team G vs Team H",
        active=True,
        closed=False,
        archived=False,
        liquidity=80_000,
        volume=120_000,
        best_bid=0.49,
        best_ask=0.51,
        last_trade_price=0.5,
        spread=0.02,
        implied_probability=0.5,
        opportunity_score=0.8,
        resolution_time=utc_now() + timedelta(days=1),
        metadata_json=overrides.get("metadata_json", {}),
    )
    db_session.add(market)
    db_session.flush()
    return market


def test_sentiment_module_returns_and_saves_usable_scores(db_session, test_settings) -> None:
    market = _market(
        db_session,
        metadata_json={
            "sentiment_items": [
                {
                    "source_type": "mock-news",
                    "headline": "Team G starter confirmed healthy and returns to lineup",
                    "team": "Team G",
                    "player": "Starter",
                }
            ]
        },
    )

    assessment = SentimentService(db_session, test_settings).assess_market(market)

    assert assessment.score > 0
    assert len(assessment.items) == 1
    assert assessment.items[0].source_text
    assert assessment.items[0].reason
    assert assessment.items[0].observed_at is not None
    assert assessment.items[0].team == "Team G"


def test_signal_scoring_uses_sentiment_and_threshold_features(db_session, test_settings) -> None:
    market = _market(
        db_session,
        metadata_json={
            "sentiment_items": [{"headline": "Team G has momentum with healthy starters confirmed"}]
        },
    )

    features = SignalService(db_session, test_settings)._features_for_market(market)
    fair_probability, _, _ = SignalService(db_session, test_settings).model_service.heuristic(
        features
    )
    edge = fair_probability - market.implied_probability
    odds_value = SignalService(db_session, test_settings)._odds_value(edge, market.spread)
    score = SignalService(db_session, test_settings).final_bet_score(
        features,
        edge,
        confidence=0.9,
        odds_value=odds_value,
    )

    assert features["sentiment_score"] > 0
    assert features["lineup_signal"] == 1.0
    assert odds_value > 0
    assert score >= test_settings.min_bet_score


def test_strategy_evaluation_compares_baseline_and_improved_rules(
    db_session, test_settings
) -> None:
    market = _market(db_session, external_id="eval-market", slug="eval-market")
    signal = Signal(
        market_id=market.id,
        mode="heuristic",
        status="traded",
        features_json={"odds_value": 0.08, "bet_score": 0.85},
        feature_importance_json={},
        market_probability=0.5,
        fair_probability=0.62,
        edge=0.12,
        expected_value_proxy=0.12,
        confidence=0.9,
        opportunity_score=0.85,
        rationale="strong historical trade",
    )
    db_session.add(signal)
    db_session.flush()
    db_session.add(
        Trade(
            market_id=market.id,
            signal_id=signal.id,
            side="buy_yes",
            status="settled",
            opened_at=utc_now() - timedelta(days=1),
            settled_at=utc_now(),
            quantity=100,
            stake=100,
            fill_price=0.5,
            exit_price=1.0,
            fees_paid=0.0,
            slippage_paid=0.0,
            realized_pnl=50.0,
            unrealized_pnl=0.0,
            confidence=0.9,
            entry_edge=0.12,
            resolution_value=1.0,
            rationale="settled winner",
            metadata_json={},
        )
    )
    db_session.commit()

    results = StrategyEvaluationService(db_session, test_settings).compare()

    assert {result.name for result in results} == {
        "baseline_edge_only",
        "improved_score_thresholds",
    }
    assert all(result.selected_trades == 1 for result in results)
