"""Settlement and postmortem generation."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.models.signal import Signal
from app.repositories.trade_repository import TradeRepository
from app.services.polymarket_client import PolymarketClient
from app.utils.time import ensure_utc, utc_now


@dataclass
class SettlementRunResult:
    settled_trades: int
    notes: list[str]


class SettlementService:
    """Settle paper trades for resolved markets and create postmortems."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.trade_repo = TradeRepository(session)
        self.polymarket_client = PolymarketClient(settings)

    def run(self) -> SettlementRunResult:
        trades = [
            trade for trade in self.trade_repo.list_trades(limit=200) if trade.status == "opened"
        ]
        settled = 0
        notes: list[str] = []
        for trade in trades:
            market = self.session.get(Market, trade.market_id)
            market = self._refresh_market_state(market)
            final_outcome = self._resolved_outcome(market)
            if final_outcome is None:
                continue
            signal = self.session.get(Signal, trade.signal_id) if trade.signal_id else None
            self.settle_trade(trade.id, final_outcome, signal)
            settled += 1
            notes.append(f"settled:{trade.id}:{final_outcome}")
        self.session.commit()
        return SettlementRunResult(settled_trades=settled, notes=notes[:10])

    def settle_trade(self, trade_id: int, outcome_yes: bool, signal: Signal | None = None) -> None:
        trade = self.trade_repo.get_trade(trade_id)
        if trade is None:
            return
        market = self.session.get(Market, trade.market_id)
        position = self.trade_repo.get_position_by_market(market.id)
        resolution_value = (
            1.0
            if (
                (trade.side == "buy_yes" and outcome_yes)
                or (trade.side == "buy_no" and not outcome_yes)
            )
            else 0.0
        )
        gross_pnl = trade.quantity * (resolution_value - trade.fill_price)
        realized_pnl = gross_pnl - trade.fees_paid
        trade.status = "settled"
        trade.closed_at = utc_now()
        trade.settled_at = utc_now()
        trade.exit_price = resolution_value
        trade.resolution_value = resolution_value
        trade.realized_pnl = round(realized_pnl, 4)
        trade.unrealized_pnl = 0.0
        trade.exit_reason = "market_resolved"

        if position is not None:
            position.status = "closed"
            position.closed_at = utc_now()
            position.market_price = resolution_value
            position.realized_pnl = round(realized_pnl, 4)
            position.unrealized_pnl = 0.0

        if self.trade_repo.get_postmortem_by_trade(trade.id) is None:
            entry_market_prob = float(
                trade.metadata_json.get("market_probability_at_entry", market.implied_probability)
            )
            fair_prob = signal.fair_probability if signal else entry_market_prob
            sizing_assessment = (
                "Sizing stayed within configured caps."
                if trade.stake
                <= self.settings.initial_bankroll * self.settings.max_position_size_pct
                else "Sizing would have breached the configured cap."
            )
            feature_drivers = signal.feature_importance_json if signal else {}
            final_result = "YES" if outcome_yes else "NO"
            lessons = (
                "Paper-trading fills and resolution timing may differ materially from live execution."
                if realized_pnl < 0
                else "Signal aligned with final outcome, but live deployability still requires stronger validation."
            )
            summary = (
                f"Entered at market probability {entry_market_prob:.2f} vs fair probability {fair_prob:.2f}; "
                f"settled {final_result} for PnL {realized_pnl:.2f}."
            )
            self.trade_repo.create_postmortem(
                {
                    "trade_id": trade.id,
                    "market_id": market.id,
                    "entry_fair_probability": round(fair_prob, 4),
                    "market_probability_at_entry": round(entry_market_prob, 4),
                    "final_result": final_result,
                    "pnl": round(realized_pnl, 4),
                    "sizing_assessment": sizing_assessment,
                    "feature_drivers_json": feature_drivers,
                    "lessons_learned": lessons,
                    "summary": summary,
                }
            )

    def _resolved_outcome(self, market: Market) -> bool | None:
        outcome = market.metadata_json.get("demo_final_outcome")
        resolution_time = ensure_utc(market.resolution_time)
        if outcome is not None and (
            market.closed or (resolution_time and resolution_time <= utc_now())
        ):
            return bool(outcome)
        return None

    def _refresh_market_state(self, market: Market) -> Market:
        refreshed = self.polymarket_client.fetch_market_by_id(market.external_id)
        if refreshed is None:
            return market

        market.active = refreshed["active"]
        market.closed = refreshed["closed"]
        market.archived = refreshed["archived"]
        market.best_bid = refreshed["best_bid"]
        market.best_ask = refreshed["best_ask"]
        market.last_trade_price = refreshed["last_trade_price"]
        market.spread = refreshed["spread"]
        market.implied_probability = refreshed["implied_probability"]
        market.resolution_time = refreshed["resolution_time"]
        market.metadata_json = {**market.metadata_json, **refreshed["metadata_json"]}

        resolved_outcome = self.polymarket_client.extract_resolved_outcome(refreshed)
        if resolved_outcome is not None:
            market.metadata_json["demo_final_outcome"] = resolved_outcome
            market.closed = True

        self.session.flush()
        return market
