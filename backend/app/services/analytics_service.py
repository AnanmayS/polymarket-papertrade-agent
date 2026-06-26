"""Portfolio and performance analytics."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.repositories.trade_repository import TradeRepository
from app.schemas.portfolio import (
    CategoryPerformance,
    EquityPoint,
    MarketPerformance,
    PortfolioRead,
)
from app.utils.math import (
    max_drawdown,
    max_drawdown_duration,
    profit_factor,
    sharpe_annualized,
    sharpe_like,
)


class AnalyticsService:
    """Compute portfolio metrics for the dashboard."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.trade_repo = TradeRepository(session)

    def snapshot(self) -> PortfolioRead:
        trades = self.trade_repo.list_trades(limit=500)
        open_positions = self.trade_repo.open_positions()
        realized_pnl = sum(trade.realized_pnl for trade in trades if trade.status == "settled")
        unrealized_pnl = sum(position.unrealized_pnl for position in open_positions)
        open_exposure = sum(position.cost_basis for position in open_positions)
        cash = self.settings.initial_bankroll - open_exposure + realized_pnl
        bankroll = cash + unrealized_pnl + open_exposure

        trade_returns = [
            trade.realized_pnl / trade.stake
            for trade in trades
            if trade.stake > 0 and trade.status == "settled"
        ]
        wins = [trade for trade in trades if trade.status == "settled" and trade.realized_pnl > 0]
        losses = [trade for trade in trades if trade.status == "settled" and trade.realized_pnl <= 0]
        settled = [trade for trade in trades if trade.status == "settled"]
        average_edge = sum(trade.entry_edge for trade in trades) / len(trades) if trades else 0.0

        # New metrics
        avg_return_per_trade = (
            sum(trade.realized_pnl for trade in settled) / len(settled) if settled else 0.0
        )
        gross_profit = sum(trade.realized_pnl for trade in wins)
        gross_loss = sum(trade.realized_pnl for trade in losses)
        pf = profit_factor(gross_profit, abs(gross_loss))
        sar = sharpe_annualized(trade_returns)

        snapshots = list(reversed(self.trade_repo.list_portfolio_snapshots(limit=200)))
        if not snapshots:
            self.trade_repo.create_portfolio_snapshot(
                {
                    "bankroll": bankroll,
                    "cash": cash,
                    "realized_pnl": realized_pnl,
                    "unrealized_pnl": unrealized_pnl,
                    "open_exposure": open_exposure,
                    "win_rate": len(wins) / len(settled) if settled else 0.0,
                    "sharpe_like": sharpe_like(trade_returns),
                    "max_drawdown": 0.0,
                }
            )
            self.session.commit()
            snapshots = list(reversed(self.trade_repo.list_portfolio_snapshots(limit=200)))

        equity_curve = [
            EquityPoint(
                timestamp=snapshot.created_at,
                bankroll=snapshot.bankroll,
                realized_pnl=snapshot.realized_pnl,
                unrealized_pnl=snapshot.unrealized_pnl,
            )
            for snapshot in snapshots
        ]
        bankroll_series = [point.bankroll for point in equity_curve]
        dd = max_drawdown(bankroll_series)
        dd_duration_hours = max_drawdown_duration(bankroll_series)
        # Convert snapshot-interval units to hours (roughly snapshot interval * count)
        snapshot_interval_hours = (
            self.settings.agent_cycle_interval_seconds / 3600 if snapshots else 1.0
        )
        dd_duration_hours = dd_duration_hours * snapshot_interval_hours

        # Per-market breakdown
        by_market: defaultdict[int, dict] = defaultdict(
            lambda: {"label": "", "realized_pnl": 0.0, "wins": 0, "trades": 0}
        )
        market_map = {market.id: market for market in self.session.query(Market).all()}
        for trade in settled:
            bucket = by_market[trade.market_id]
            bucket["label"] = (
                market_map.get(trade.market_id).question
                if trade.market_id in market_map
                else f"Market {trade.market_id}"
            )
            bucket["realized_pnl"] += trade.realized_pnl
            bucket["wins"] += int(trade.realized_pnl > 0)
            bucket["trades"] += 1

        per_market = [
            MarketPerformance(
                market_id=market_id,
                label=values["label"],
                realized_pnl=round(values["realized_pnl"], 2),
                trades=values["trades"],
                win_rate=(values["wins"] / values["trades"]) if values["trades"] else 0.0,
            )
            for market_id, values in by_market.items()
        ]
        per_market = sorted(per_market, key=lambda item: item.realized_pnl, reverse=True)

        # Per-category breakdown
        by_category: defaultdict[str, dict] = defaultdict(
            lambda: {"realized_pnl": 0.0, "trades": 0, "wins": 0}
        )
        for trade in settled:
            m = market_map.get(trade.market_id)
            cat = m.category if m else "unknown"
            bucket = by_category[cat]
            bucket["realized_pnl"] += trade.realized_pnl
            bucket["trades"] += 1
            if trade.realized_pnl > 0:
                bucket["wins"] += 1

        per_category = [
            CategoryPerformance(
                category=cat,
                realized_pnl=round(values["realized_pnl"], 2),
                trades=values["trades"],
                wins=values["wins"],
                losses=values["trades"] - values["wins"],
                win_rate=round(values["wins"] / values["trades"], 4) if values["trades"] else 0.0,
            )
            for cat, values in sorted(by_category.items())
        ]

        # Drawdown series for chart overlay
        drawdown_series = []
        if bankroll_series:
            peak = bankroll_series[0]
            for value in bankroll_series:
                peak = max(peak, value)
                d = (peak - value) / peak if peak else 0.0
                drawdown_series.append(round(d, 4))

        # pandas keeps the portfolio analytics logic concise and easy to inspect.
        if settled:
            _ = pd.DataFrame(
                [{"created_at": trade.created_at, "pnl": trade.realized_pnl} for trade in settled]
            )

        return PortfolioRead(
            bankroll=round(bankroll, 2),
            cash=round(cash, 2),
            realized_pnl=round(realized_pnl, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            current_equity=round(cash + open_exposure + unrealized_pnl, 2),
            open_exposure=round(open_exposure, 2),
            win_rate=round(len(wins) / len(settled), 4) if settled else 0.0,
            average_edge=round(average_edge, 4),
            sharpe_like=round(sharpe_like(trade_returns), 4),
            sharpe_annualized=round(sar, 4),
            max_drawdown=round(dd, 4),
            max_drawdown_duration_hours=round(dd_duration_hours, 2),
            avg_return_per_trade=round(avg_return_per_trade, 2),
            profit_factor=pf,
            open_positions=open_positions,
            equity_curve=equity_curve,
            per_market=per_market,
            per_category=per_category,
            drawdown_series=drawdown_series,
        )

    def persist_snapshot(self) -> None:
        portfolio = self.snapshot()
        self.trade_repo.create_portfolio_snapshot(
            {
                "bankroll": portfolio.bankroll,
                "cash": portfolio.cash,
                "realized_pnl": portfolio.realized_pnl,
                "unrealized_pnl": portfolio.unrealized_pnl,
                "open_exposure": portfolio.open_exposure,
                "win_rate": portfolio.win_rate,
                "sharpe_like": portfolio.sharpe_like,
                "max_drawdown": portfolio.max_drawdown,
            }
        )
        self.session.commit()
