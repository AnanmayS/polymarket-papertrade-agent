"""Probability model service supporting heuristic and ML modes."""

from __future__ import annotations

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.signal import Signal
from app.models.trade import Trade
from app.repositories.signal_repository import SignalRepository
from app.utils.math import clamp

try:
    from xgboost import XGBClassifier
except Exception:  # noqa: BLE001
    XGBClassifier = None

from sklearn.linear_model import LogisticRegression

FEATURE_KEYS = [
    "market_probability",
    "spread",
    "liquidity_score",
    "volume_score",
    "momentum_1h",
    "momentum_24h",
    "mean_reversion_gap",
]


class ProbabilityModelService:
    """Estimate fair probability from heuristic or fitted historical models."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = SignalRepository(session)

    def heuristic(self, features: dict[str, float]) -> tuple[float, dict[str, float], str]:
        market_prob = features["market_probability"]
        momentum_component = (features["momentum_1h"] * 0.6) + (features["momentum_24h"] * 0.4)
        liquidity_component = (features["liquidity_score"] - 0.5) * 0.04
        spread_penalty = (0.5 - features["spread"]) * 0.04
        mean_reversion_component = features["mean_reversion_gap"] * 0.15
        fair_prob = clamp(
            market_prob
            + (momentum_component * 0.35)
            + liquidity_component
            + spread_penalty
            - mean_reversion_component,
            0.02,
            0.98,
        )
        importance = {
            "momentum_component": round(momentum_component, 4),
            "liquidity_component": round(liquidity_component, 4),
            "spread_penalty": round(spread_penalty, 4),
            "mean_reversion_component": round(mean_reversion_component, 4),
        }
        rationale = (
            "Heuristic fair probability blends market price with short-term momentum, "
            "liquidity quality, and spread efficiency. Paper-trading estimates do not imply live edge."
        )
        return fair_prob, importance, rationale

    def ml_probability(
        self, features: dict[str, float]
    ) -> tuple[float, dict[str, float], str, int, str]:
        train_rows = self._training_rows()
        if len(train_rows) < 8:
            fair_prob, importance, rationale = self.heuristic(features)
            return (
                fair_prob,
                importance,
                f"{rationale} Fallback: not enough settled paper trades for ML.",
                len(train_rows),
                "heuristic-fallback",
            )

        x = np.array([[row[key] for key in FEATURE_KEYS] for row, _ in train_rows], dtype=float)
        y = np.array([label for _, label in train_rows], dtype=int)
        current = np.array([[features[key] for key in FEATURE_KEYS]], dtype=float)

        if XGBClassifier is not None and len(train_rows) >= 20:
            model = XGBClassifier(
                n_estimators=40,
                max_depth=3,
                learning_rate=0.1,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
            )
            model.fit(x, y)
            fair_prob = float(model.predict_proba(current)[0][1])
            importance = {
                FEATURE_KEYS[index]: round(score, 4)
                for index, score in enumerate(model.feature_importances_.tolist())
            }
            model_name = "xgboost"
        else:
            model = LogisticRegression(max_iter=1000)
            model.fit(x, y)
            fair_prob = float(model.predict_proba(current)[0][1])
            importance = {
                FEATURE_KEYS[index]: round(float(score), 4)
                for index, score in enumerate(model.coef_[0].tolist())
            }
            model_name = "logistic_regression"

        rationale = (
            f"ML fair probability estimated with {model_name} trained on settled paper-trade features. "
            "This is a research baseline, not evidence of production alpha."
        )
        return clamp(fair_prob, 0.02, 0.98), importance, rationale, len(train_rows), model_name

    def record_run(self, mode: str, model_name: str, training_samples: int, notes: str) -> int:
        run = self.repo.create_model_run(
            {
                "mode": mode,
                "model_name": model_name,
                "training_samples": training_samples,
                "metrics_json": {"training_samples": training_samples},
                "notes": notes,
            }
        )
        self.session.flush()
        return run.id

    def _training_rows(self) -> list[tuple[dict[str, float], int]]:
        stmt = (
            select(Signal, Trade)
            .join(Trade, Trade.signal_id == Signal.id)
            .where(Trade.status == "settled")
        )
        rows = self.session.execute(stmt).all()
        train_rows: list[tuple[dict[str, float], int]] = []
        for signal, trade in rows:
            features = {key: float(signal.features_json.get(key, 0.0)) for key in FEATURE_KEYS}
            label = 1 if (trade.realized_pnl or 0.0) > 0 else 0
            train_rows.append((features, label))
        return train_rows
