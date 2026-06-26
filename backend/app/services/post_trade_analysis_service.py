"""Post-trade analysis and strategy comparison service."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.models.signal import Signal
from app.models.trade import Trade
from app.repositories.trade_repository import TradeRepository
from app.utils.math import max_drawdown, profit_factor, sharpe_like


class PostTradeAnalysisService:
    """Analyse settled trades for strategy insights, patterns, and export."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.trade_repo = TradeRepository(session)

    def _settled_trades(self) -> list[Trade]:
        return self.trade_repo.list_trades(limit=500, statuses=("settled",))

    def _settled_with_signals(self) -> list[tuple[Trade, Signal | None, Market | None]]:
        trades = self._settled_trades()
        market_ids = {t.market_id for t in trades}
        signal_ids = {t.signal_id for t in trades if t.signal_id}
        markets = {
            m.id: m
            for m in self.session.scalars(
                select(Market).where(Market.id.in_(market_ids))
            )
        }
        signals = (
            {
                s.id: s
                for s in self.session.scalars(
                    select(Signal).where(Signal.id.in_(signal_ids))
                )
            }
            if signal_ids
            else {}
        )
        return [(t, signals.get(t.signal_id) if t.signal_id else None, markets.get(t.market_id)) for t in trades]

    def _market_map(self, trades: list[Trade]) -> dict[int, Market]:
        market_ids = {t.market_id for t in trades}
        return {
            m.id: m
            for m in self.session.scalars(
                select(Market).where(Market.id.in_(market_ids))
            )
        }

    # ----------------------------------------------------------------
    # Per-strategy performance breakdown
    # ----------------------------------------------------------------
    def strategy_performance(self) -> list[dict]:
        """Break down PnL by signal mode (heuristic, ml) and signal type."""
        rows = self._settled_with_signals()
        by_mode: defaultdict[str, dict] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "realized_pnl": 0.0, "total_edge": 0.0}
        )
        for trade, signal, _market in rows:
            mode = signal.mode if signal else "unknown"
            bucket = by_mode[mode]
            bucket["trades"] += 1
            bucket["realized_pnl"] += trade.realized_pnl
            bucket["total_edge"] += abs(trade.entry_edge)
            if trade.realized_pnl > 0:
                bucket["wins"] += 1

        return [
            {
                "mode": mode,
                "trades": v["trades"],
                "wins": v["wins"],
                "losses": v["trades"] - v["wins"],
                "win_rate": round(v["wins"] / v["trades"], 4) if v["trades"] else 0.0,
                "realized_pnl": round(v["realized_pnl"], 2),
                "avg_edge": round(v["total_edge"] / v["trades"], 4) if v["trades"] else 0.0,
                "avg_pnl_per_trade": round(v["realized_pnl"] / v["trades"], 2) if v["trades"] else 0.0,
            }
            for mode, v in sorted(by_mode.items())
        ]

    # ----------------------------------------------------------------
    # Time-of-day / day-of-week patterns
    # ----------------------------------------------------------------
    def temporal_patterns(self) -> dict:
        """Analyse performance by hour-of-day and day-of-week."""
        rows = self._settled_with_signals()
        by_hour: defaultdict[int, dict] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "realized_pnl": 0.0}
        )
        by_dow: defaultdict[str, dict] = defaultdict(
            lambda: {"trades": 0, "wins": 0, "realized_pnl": 0.0}
        )

        for trade, _signal, _market in rows:
            if not trade.opened_at:
                continue
            local_hour = trade.opened_at.hour
            dow = trade.opened_at.strftime("%A")

            hour_b = by_hour[local_hour]
            hour_b["trades"] += 1
            hour_b["realized_pnl"] += trade.realized_pnl
            if trade.realized_pnl > 0:
                hour_b["wins"] += 1

            dow_b = by_dow[dow]
            dow_b["trades"] += 1
            dow_b["realized_pnl"] += trade.realized_pnl
            if trade.realized_pnl > 0:
                dow_b["wins"] += 1

        DOW_ORDER = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]

        return {
            "by_hour": [
                {
                    "hour": h,
                    "trades": v["trades"],
                    "win_rate": round(v["wins"] / v["trades"], 4) if v["trades"] else 0.0,
                    "realized_pnl": round(v["realized_pnl"], 2),
                }
                for h, v in sorted(by_hour.items())
            ],
            "by_day_of_week": [
                {
                    "day": d,
                    "trades": v["trades"],
                    "win_rate": round(v["wins"] / v["trades"], 4) if v["trades"] else 0.0,
                    "realized_pnl": round(v["realized_pnl"], 2),
                }
                for d in DOW_ORDER
                if (v := by_dow.get(d))
            ],
        }

    # ----------------------------------------------------------------
    # Market microstructure analysis
    # ----------------------------------------------------------------
    def microstructure_analysis(self) -> dict:
        """Analyse spread capture, slippage impact, and adverse selection."""
        trades = self._settled_trades()
        if not trades:
            return {}

        markets = self._market_map(trades)

        total_slippage = sum(abs(t.slippage_paid) for t in trades)
        total_fees = sum(t.fees_paid for t in trades)
        total_costs = total_slippage + total_fees
        total_pnl = sum(t.realized_pnl for t in trades)
        total_spread = sum(
            markets[t.market_id].spread if t.market_id in markets else 0.0
            for t in trades
        )

        # Adverse selection: how often does the market move against the entry
        adverse_losses = 0
        favorable = 0
        for trade in trades:
            if trade.side == "buy_yes":
                adverse = trade.exit_price < trade.fill_price
            else:
                adverse = trade.exit_price > (1 - trade.fill_price)
            if adverse:
                adverse_losses += 1
            else:
                favorable += 1

        # Spread capture: spread-to-PnL ratio
        spread_to_pnl_ratio = (
            total_spread / abs(total_pnl) if abs(total_pnl) > 0 else 0.0
        )

        return {
            "total_spread_paid": round(total_spread, 4),
            "total_slippage_paid": round(total_slippage, 4),
            "total_fees_paid": round(total_fees, 4),
            "total_costs_paid": round(total_costs, 4),
            "costs_as_pct_of_pnl": round(
                total_costs / abs(total_pnl) * 100 if abs(total_pnl) > 0 else 0.0, 2
            ),
            "avg_spread_per_trade": round(total_spread / len(trades), 4) if trades else 0.0,
            "avg_slippage_per_trade": round(total_slippage / len(trades), 4) if trades else 0.0,
            "avg_fees_per_trade": round(total_fees / len(trades), 4) if trades else 0.0,
            "spread_to_pnl_ratio": round(spread_to_pnl_ratio, 4),
            "adverse_selection": {
                "adverse_trades": adverse_losses,
                "favorable_trades": favorable,
                "adverse_rate": round(
                    adverse_losses / (favorable + adverse_losses), 4
                )
                if (favorable + adverse_losses) > 0
                else 0.0,
            },
            "avg_trade_length_hours": self._avg_trade_duration(trades),
        }

    def _avg_trade_duration(self, trades: list[Trade]) -> float:
        durations = [
            (trade.settled_at - trade.opened_at).total_seconds() / 3600
            for trade in trades
            if trade.opened_at and trade.settled_at
        ]
        return round(sum(durations) / len(durations), 2) if durations else 0.0

    # ----------------------------------------------------------------
    # Strategy A/B comparison over same time period
    # ----------------------------------------------------------------
    def strategy_ab_comparison(self) -> dict:
        """Compare heuristic vs ML strategies over overlapping time periods."""
        rows = self._settled_with_signals()
        if not rows:
            return {}

        # Find overlapping date range
        dates = [t.opened_at.date() for t, _, _ in rows if t.opened_at]
        if not dates:
            return {}
        min_date = min(dates)
        max_date = max(dates)

        by_mode: defaultdict[str, list[Trade]] = defaultdict(list)
        for trade, signal, _market in rows:
            mode = signal.mode if signal else "unknown"
            by_mode[mode].append(trade)

        strategies = {}
        for mode, mode_trades in by_mode.items():
            returns = [
                t.realized_pnl / t.stake for t in mode_trades if t.stake > 0
            ]
            wins = sum(1 for t in mode_trades if t.realized_pnl > 0)
            losses = len(mode_trades) - wins
            gross_profit = sum(t.realized_pnl for t in mode_trades if t.realized_pnl > 0)
            gross_loss = sum(t.realized_pnl for t in mode_trades if t.realized_pnl < 0)

            strategies[mode] = {
                "trades": len(mode_trades),
                "wins": wins,
                "losses": losses,
                "win_rate": round(wins / len(mode_trades), 4) if mode_trades else 0.0,
                "realized_pnl": round(sum(t.realized_pnl for t in mode_trades), 2),
                "avg_return_per_trade": round(
                    sum(t.realized_pnl for t in mode_trades) / len(mode_trades), 2
                )
                if mode_trades
                else 0.0,
                "sharpe": round(sharpe_like(returns), 4),
                "profit_factor": profit_factor(gross_profit, abs(gross_loss)),
                "max_drawdown": round(
                    max_drawdown(self._equity_series(mode_trades)), 4
                ),
            }

        return {
            "period": {
                "start": min_date.isoformat(),
                "end": max_date.isoformat(),
            },
            "strategies": strategies,
        }

    @staticmethod
    def _equity_series(trades: list[Trade]) -> list[float]:
        cumulative = 0.0
        series = []
        for t in sorted(trades, key=lambda x: x.opened_at or datetime.min):
            cumulative += t.realized_pnl
            series.append(cumulative)
        return series

    # ----------------------------------------------------------------
    # Export trade log as CSV
    # ----------------------------------------------------------------
    def export_csv(self, status: str | None = None) -> str:
        """Export trade log as CSV string."""
        statuses: tuple[str, ...] | None = None
        if status and status in ("opened", "settled"):
            statuses = (status,)

        trades = self.trade_repo.list_trades(limit=1000, statuses=statuses)
        markets = self._market_map(trades)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "market_id",
                "market_question",
                "category",
                "side",
                "status",
                "stake",
                "quantity",
                "fill_price",
                "exit_price",
                "fees_paid",
                "slippage_paid",
                "realized_pnl",
                "entry_edge",
                "confidence",
                "opened_at",
                "settled_at",
                "rationale",
            ]
        )
        for trade in trades:
            market = markets.get(trade.market_id)
            writer.writerow(
                [
                    trade.id,
                    trade.market_id,
                    market.question if market else "",
                    market.category if market else "",
                    trade.side,
                    trade.status,
                    trade.stake,
                    trade.quantity,
                    trade.fill_price,
                    trade.exit_price,
                    trade.fees_paid,
                    trade.slippage_paid,
                    trade.realized_pnl,
                    trade.entry_edge,
                    trade.confidence,
                    trade.opened_at.isoformat() if trade.opened_at else "",
                    trade.settled_at.isoformat() if trade.settled_at else "",
                    trade.rationale,
                ]
            )
        return output.getvalue()
