"""Signal generation pipeline."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.repositories.market_repository import MarketRepository
from app.repositories.signal_repository import SignalRepository
from app.services.model_service import ProbabilityModelService
from app.services.sentiment_service import SentimentService
from app.utils.math import clamp, edge_from_probabilities, expected_value_proxy


@dataclass
class SignalRunResult:
    signals_created: int
    notes: list[str]


class SignalService:
    """Generate heuristic or ML signals from market microstructure features."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.market_repo = MarketRepository(session)
        self.signal_repo = SignalRepository(session)
        self.model_service = ProbabilityModelService(session, settings)
        self.sentiment_service = SentimentService(session, settings)

    def run(self, mode: str | None = None) -> SignalRunResult:
        selected_mode = mode or self.settings.default_signal_mode
        markets = self.market_repo.list_candidate_markets(limit=50)
        created = 0
        notes: list[str] = []
        for market in markets:
            features = self._features_for_market(market)
            if selected_mode == "ml":
                fair_probability, importance, rationale, samples, model_name = (
                    self.model_service.ml_probability(features)
                )
                model_run_id = self.model_service.record_run("ml", model_name, samples, rationale)
            else:
                fair_probability, importance, rationale = self.model_service.heuristic(features)
                model_run_id = self.model_service.record_run(
                    "heuristic", "rule_blend", 0, rationale
                )

            market_probability = features["market_probability"]
            edge = edge_from_probabilities(fair_probability, market_probability)
            odds_value = self._odds_value(edge, market.spread)
            confidence = clamp(
                0.25
                + (abs(edge) * 8)
                + (market.opportunity_score * 0.35)
                + (features["liquidity_score"] * 0.1),
                0.0,
                0.99,
            )
            bet_score = self.final_bet_score(features, edge, confidence, odds_value)
            features["odds_value"] = odds_value
            features["bet_score"] = bet_score
            signal = self.signal_repo.create_signal(
                {
                    "market_id": market.id,
                    "model_run_id": model_run_id,
                    "mode": selected_mode,
                    "status": "candidate",
                    "features_json": features,
                    "feature_importance_json": importance,
                    "market_probability": market_probability,
                    "fair_probability": fair_probability,
                    "edge": edge,
                    "expected_value_proxy": expected_value_proxy(
                        fair_probability, market_probability
                    ),
                    "confidence": confidence,
                    "opportunity_score": market.opportunity_score,
                    "rationale": (
                        f"{rationale} Estimated edge: {edge:.2%}. Confidence score: {confidence:.0%}."
                    ),
                }
            )
            created += 1
            notes.append(f"signal:{signal.id}:market:{market.slug}")
        self.session.commit()
        return SignalRunResult(signals_created=created, notes=notes[:10])

    def _features_for_market(self, market: Market) -> dict[str, float]:
        latest = self.market_repo.latest_snapshot(market.id)
        momentum_1h = latest.price_change_1h if latest else 0.0
        momentum_24h = latest.price_change_24h if latest else 0.0
        average_price = (
            np.mean(
                [
                    item
                    for item in [market.best_bid, market.best_ask, market.last_trade_price]
                    if item > 0
                ]
            )
            if any([market.best_bid, market.best_ask, market.last_trade_price])
            else market.implied_probability
        )
        mean_reversion_gap = market.implied_probability - average_price
        sentiment_assessment = self.sentiment_service.assess_market(market)
        lineup_signal = 1.0 if self._has_lineup_context(market) else 0.0
        return {
            "market_probability": market.implied_probability,
            "spread": market.spread,
            "liquidity_score": clamp(
                market.liquidity / max(self.settings.min_liquidity * 4, 1.0), 0.0, 1.0
            ),
            "volume_score": clamp(market.volume / max(self.settings.min_volume * 4, 1.0), 0.0, 1.0),
            "momentum_1h": momentum_1h,
            "momentum_24h": momentum_24h,
            "mean_reversion_gap": mean_reversion_gap,
            "sentiment_score": sentiment_assessment.score,
            "lineup_signal": lineup_signal,
        }

    def _has_lineup_context(self, market: Market) -> bool:
        metadata = market.metadata_json or {}
        raw_items = metadata.get("sentiment_items")
        if not isinstance(raw_items, list):
            return False
        terms = ("lineup", "starter", "healthy", "injury", "injured", "out", "questionable")
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            text = str(item.get("source_text") or item.get("headline") or "").lower()
            if any(term in text for term in terms):
                return True
        return False

    def _odds_value(self, edge: float, spread: float) -> float:
        """Score edge quality after accounting for spread friction."""

        return round(max(abs(edge) - (spread / 2), 0.0), 4)

    def final_bet_score(
        self,
        features: dict[str, float],
        edge: float,
        confidence: float,
        odds_value: float,
    ) -> float:
        """Blend market quality, edge, confidence, and sentiment into one threshold score."""

        score = (
            (abs(edge) * 3.0)
            + (odds_value * 2.0)
            + (confidence * 0.35)
            + (features["liquidity_score"] * 0.1)
            + (features["volume_score"] * 0.1)
            + (max(features["sentiment_score"], 0.0) * 0.25)
            + (features["lineup_signal"] * 0.1)
        )
        return round(clamp(score, 0.0, 1.0), 4)
