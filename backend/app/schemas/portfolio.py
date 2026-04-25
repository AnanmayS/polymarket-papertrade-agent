"""Portfolio schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.trade import PositionRead


class EquityPoint(BaseModel):
    timestamp: datetime
    bankroll: float
    realized_pnl: float
    unrealized_pnl: float


class MarketPerformance(BaseModel):
    market_id: int
    label: str
    realized_pnl: float
    trades: int
    win_rate: float


class PortfolioRead(BaseModel):
    bankroll: float
    cash: float
    realized_pnl: float
    unrealized_pnl: float
    current_equity: float
    open_exposure: float
    win_rate: float
    average_edge: float
    sharpe_like: float
    max_drawdown: float
    open_positions: list[PositionRead]
    equity_curve: list[EquityPoint]
    per_market: list[MarketPerformance]
