"""Lightweight historical strategy evaluation.

This is not a full backtester. It compares threshold rules on already-settled
paper trades so model changes can be sanity-checked without overfitting.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.signal import Signal
from app.models.trade import Trade


@dataclass
class StrategyEvaluation:
    name: str
    selected_trades: int
    win_rate: float
    realized_pnl: float
    average_edge: float


class StrategyEvaluationService:
    """Compare baseline and improved selection rules on settled paper trades."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def compare(self) -> list[StrategyEvaluation]:
        rows = self.session.execute(
            select(Signal, Trade)
            .join(Trade, Trade.signal_id == Signal.id)
            .where(Trade.status == "settled")
        ).all()
        return [
            self._evaluate("baseline_edge_only", rows, self._baseline_rule),
            self._evaluate("improved_score_thresholds", rows, self._improved_rule),
        ]

    def _baseline_rule(self, signal: Signal) -> bool:
        return abs(signal.edge) >= 0.025

    def _improved_rule(self, signal: Signal) -> bool:
        odds_value = float(signal.features_json.get("odds_value", signal.expected_value_proxy))
        bet_score = float(signal.features_json.get("bet_score", signal.opportunity_score))
        return (
            abs(signal.edge) >= self.settings.min_edge_to_trade
            and odds_value >= self.settings.min_odds_value
            and signal.confidence >= self.settings.min_confidence
            and bet_score >= self.settings.min_bet_score
        )

    def _evaluate(self, name: str, rows, rule) -> StrategyEvaluation:
        selected = [(signal, trade) for signal, trade in rows if rule(signal)]
        wins = [trade for _, trade in selected if trade.realized_pnl > 0]
        realized_pnl = sum(trade.realized_pnl for _, trade in selected)
        average_edge = (
            sum(abs(signal.edge) for signal, _ in selected) / len(selected) if selected else 0.0
        )
        return StrategyEvaluation(
            name=name,
            selected_trades=len(selected),
            win_rate=round(len(wins) / len(selected), 4) if selected else 0.0,
            realized_pnl=round(realized_pnl, 2),
            average_edge=round(average_edge, 4),
        )
