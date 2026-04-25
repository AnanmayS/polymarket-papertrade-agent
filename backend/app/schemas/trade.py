"""Trade schemas."""

from datetime import datetime

from app.schemas.common import TimeStamped


class TradeRead(TimeStamped):
    id: int
    market_id: int
    signal_id: int | None
    risk_decision_id: int | None
    side: str
    status: str
    proposed_at: datetime | None
    approved_at: datetime | None
    opened_at: datetime | None
    closed_at: datetime | None
    settled_at: datetime | None
    quantity: float
    stake: float
    fill_price: float
    exit_price: float
    fees_paid: float
    slippage_paid: float
    realized_pnl: float
    unrealized_pnl: float
    confidence: float
    entry_edge: float
    resolution_value: float | None
    rationale: str
    exit_reason: str | None
    metadata_json: dict


class PositionRead(TimeStamped):
    id: int
    market_id: int
    side: str
    status: str
    quantity: float
    avg_price: float
    cost_basis: float
    market_price: float
    realized_pnl: float
    unrealized_pnl: float
    opened_at: datetime | None
    closed_at: datetime | None
    metadata_json: dict
