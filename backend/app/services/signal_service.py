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
from app.utils.math import clamp, edge_from_probabilities, expected_value_proxy


@dataclass
class SignalRunResult:
    signals_created: int
    notes: list[str]


class SentimentAdapter:
    """Placeholder interface for future Reddit/X/news adapters."""

    def get_score(self, market: Market) -> float:
        return 0.0


class SignalService:
    """Generate heuristic or ML signals from market microstructure features."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.market_repo = MarketRepository(session)
        self.signal_repo = SignalRepository(session)
        self.model_service = ProbabilityModelService(session, settings)
        self.sentiment_adapter = SentimentAdapter()

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
            confidence = clamp(
                0.25
                + (abs(edge) * 8)
                + (market.opportunity_score * 0.35)
                + (features["liquidity_score"] * 0.1),
                0.0,
                0.99,
            )
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
            "sentiment_score": self.sentiment_adapter.get_score(market),
        }
