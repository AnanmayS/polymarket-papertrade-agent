"""Paper execution service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.models.risk import RiskDecision
from app.models.signal import Signal
from app.models.trade import Trade
from app.repositories.trade_repository import TradeRepository
from app.utils.math import clamp
from app.utils.time import utc_now


@dataclass
class ExecutionRunResult:
    trades_created: int
    notes: list[str]


class PaperExecutionService:
    """Simulate fills, fees, and position opens without real money."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.trade_repo = TradeRepository(session)

    def run(self) -> ExecutionRunResult:
        decisions = list(
            self.session.scalars(
                select(RiskDecision)
                .where(RiskDecision.approved.is_(True))
                .order_by(RiskDecision.created_at.desc())
            )
        )
        created = 0
        notes: list[str] = []
        for decision in decisions:
            existing_trade = self.session.scalar(
                select(Trade).where(Trade.risk_decision_id == decision.id)
            )
            if existing_trade is not None:
                continue
            if self.session.scalar(select(Signal).where(Signal.id == decision.signal_id)) is None:
                continue
            signal = self.session.get(Signal, decision.signal_id)
            market = self.session.get(Market, decision.market_id)
            if self.trade_repo.get_position_by_market(market.id) is not None:
                continue
            trade = self.execute_trade(signal, decision, market)
            created += 1
            notes.append(f"trade:{trade.id}:{trade.side}")
        self.session.commit()
        return ExecutionRunResult(trades_created=created, notes=notes[:10])

    def execute_trade(self, signal: Signal, decision: RiskDecision, market: Market):
        side = "buy_yes" if signal.edge >= 0 else "buy_no"
        reference_price = (
            market.implied_probability if side == "buy_yes" else (1 - market.implied_probability)
        )
        reference_price = clamp(reference_price, 0.01, 0.99)
        spread_half = market.spread / 2
        slippage = reference_price * (self.settings.slippage_bps / 10_000)
        fill_price = clamp(reference_price + spread_half + slippage, 0.01, 0.99)
        stake = decision.proposed_stake
        quantity = (stake / fill_price) * self.settings.partial_fill_ratio
        fees = stake * (self.settings.fee_bps / 10_000)
        trade = self.trade_repo.create_trade(
            {
                "market_id": market.id,
                "signal_id": signal.id,
                "risk_decision_id": decision.id,
                "side": side,
                "status": "opened",
                "proposed_at": utc_now(),
                "approved_at": utc_now(),
                "opened_at": utc_now(),
                "quantity": round(quantity, 4),
                "stake": round(stake, 2),
                "fill_price": round(fill_price, 4),
                "fees_paid": round(fees, 4),
                "slippage_paid": round(slippage * quantity, 4),
                "confidence": signal.confidence,
                "entry_edge": signal.edge,
                "rationale": signal.rationale,
                "metadata_json": {
                    "partial_fill_ratio": self.settings.partial_fill_ratio,
                    "market_probability_at_entry": market.implied_probability,
                    "paper_trading_only": True,
                },
            }
        )
        signal.status = "traded"
        current_market_price = (
            market.implied_probability if side == "buy_yes" else (1 - market.implied_probability)
        )
        unrealized_pnl = (quantity * (current_market_price - fill_price)) - fees
        self.trade_repo.upsert_position(
            {
                "market_id": market.id,
                "side": side,
                "status": "open",
                "quantity": round(quantity, 4),
                "avg_price": round(fill_price, 4),
                "cost_basis": round(stake, 2),
                "market_price": round(current_market_price, 4),
                "realized_pnl": 0.0,
                "unrealized_pnl": round(unrealized_pnl, 4),
                "opened_at": utc_now(),
                "metadata_json": {"confidence": signal.confidence},
            }
        )
        return trade
