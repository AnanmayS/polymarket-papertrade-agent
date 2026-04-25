"""Risk evaluation and position sizing."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.models.risk import RiskDecision
from app.models.signal import Signal
from app.repositories.signal_repository import SignalRepository
from app.repositories.trade_repository import TradeRepository
from app.services.analytics_service import AnalyticsService
from app.utils.math import clamp, kelly_fraction


@dataclass
class RiskRunResult:
    decisions_created: int
    notes: list[str]


@dataclass
class RiskState:
    """Mutable approval state used within a single risk-engine pass."""

    bankroll: float
    available_cash: float
    daily_realized_loss: float
    open_trade_count: int
    market_exposure: dict[int, float] = field(default_factory=dict)
    category_exposure: dict[str, float] = field(default_factory=dict)


class RiskService:
    """Apply bankroll-aware approval rules for paper trades."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.signal_repo = SignalRepository(session)
        self.trade_repo = TradeRepository(session)
        self.analytics_service = AnalyticsService(session, settings)

    def evaluate_signals(self) -> RiskRunResult:
        signals = self.signal_repo.list_signals(limit=100)
        created = 0
        notes: list[str] = []
        risk_state = self._build_risk_state()
        for signal in signals:
            if (
                self.session.scalar(select(RiskDecision).where(RiskDecision.signal_id == signal.id))
                is not None
            ):
                continue
            market = self.session.get(Market, signal.market_id)
            if market is None:
                continue
            decision = self.evaluate_signal(signal, market, risk_state=risk_state)
            created += 1
            notes.append(f"risk:{decision.id}:{'approved' if decision.approved else 'blocked'}")
        self.session.commit()
        return RiskRunResult(decisions_created=created, notes=notes[:10])

    def evaluate_signal(
        self, signal: Signal, market: Market, risk_state: RiskState | None = None
    ) -> RiskDecision:
        risk_state = risk_state or self._build_risk_state()
        return self._evaluate_signal(signal, market, risk_state)

    def _build_risk_state(self) -> RiskState:
        portfolio = self.analytics_service.snapshot()
        open_positions = self.trade_repo.open_positions()
        daily_realized_loss = sum(
            abs(min(trade.realized_pnl, 0.0))
            for trade in self.trade_repo.list_trades(limit=200)
            if trade.status == "settled"
        )
        market_exposure: defaultdict[int, float] = defaultdict(float)
        category_exposure: defaultdict[str, float] = defaultdict(float)
        for position in open_positions:
            market_exposure[position.market_id] += position.cost_basis
            position_market = self.session.get(Market, position.market_id)
            category = position_market.category if position_market is not None else "unknown"
            category_exposure[category] += position.cost_basis
        return RiskState(
            bankroll=portfolio.bankroll,
            available_cash=portfolio.cash,
            daily_realized_loss=daily_realized_loss,
            open_trade_count=len(open_positions),
            market_exposure=dict(market_exposure),
            category_exposure=dict(category_exposure),
        )

    def _evaluate_signal(self, signal: Signal, market: Market, risk_state: RiskState) -> RiskDecision:
        reasons: list[str] = []
        proposed_stake = self.size_position(signal, risk_state.bankroll)
        available_cash_before = risk_state.available_cash
        market_exposure = risk_state.market_exposure.get(market.id, 0.0)
        category_exposure = risk_state.category_exposure.get(market.category, 0.0)

        if abs(signal.edge) < self.settings.min_edge_to_trade:
            reasons.append("edge_too_small")
        if signal.confidence < self.settings.min_confidence:
            reasons.append("confidence_below_threshold")
        if risk_state.open_trade_count >= self.settings.max_open_trades:
            reasons.append("max_open_trades_reached")
        if (
            risk_state.daily_realized_loss
            >= risk_state.bankroll * self.settings.max_daily_loss_pct
        ):
            reasons.append("max_daily_loss_reached")
        if proposed_stake > risk_state.bankroll * self.settings.max_position_size_pct:
            reasons.append("position_size_cap_exceeded")
        if proposed_stake > risk_state.available_cash:
            reasons.append("insufficient_cash")
        if (
            market_exposure + proposed_stake
            > risk_state.bankroll * self.settings.max_market_exposure_pct
        ):
            reasons.append("market_exposure_cap_exceeded")
        if (
            category_exposure + proposed_stake
            > risk_state.bankroll * self.settings.max_category_exposure_pct
        ):
            reasons.append("category_exposure_cap_exceeded")
        if proposed_stake <= 0:
            reasons.append("non_positive_stake")

        approved = not reasons
        signal.status = "approved" if approved else "blocked"
        if approved:
            risk_state.available_cash -= proposed_stake
            risk_state.open_trade_count += 1
            risk_state.market_exposure[market.id] = market_exposure + proposed_stake
            risk_state.category_exposure[market.category] = category_exposure + proposed_stake
        decision = self.signal_repo.create_risk_decision(
            {
                "market_id": market.id,
                "signal_id": signal.id,
                "approved": approved,
                "reason_codes": reasons or ["approved"],
                "bankroll_before": risk_state.bankroll,
                "proposed_stake": round(proposed_stake, 2),
                "confidence": signal.confidence,
                "details_json": {
                    "edge": signal.edge,
                    "market_exposure": market_exposure,
                    "category_exposure": category_exposure,
                    "available_cash_before": round(available_cash_before, 2),
                    "market": market.question,
                },
            }
        )
        return decision

    def size_position(self, signal: Signal, bankroll: float, use_kelly: bool = False) -> float:
        base_cap = bankroll * self.settings.max_position_size_pct
        if use_kelly:
            kelly = kelly_fraction(signal.fair_probability, signal.market_probability)
            return round(min(base_cap, bankroll * kelly * self.settings.fractional_kelly), 2)
        conviction = clamp((abs(signal.edge) * 10) + (signal.confidence * 0.5), 0.0, 1.0)
        return round(base_cap * conviction, 2)
