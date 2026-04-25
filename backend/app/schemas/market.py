"""Market API schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimeStamped


class MarketRead(TimeStamped):
    id: int
    external_id: str
    slug: str
    question: str
    category: str
    subcategory: str | None
    sports_league: str | None
    event_title: str | None
    active: bool
    closed: bool
    archived: bool
    liquidity: float
    volume: float
    best_bid: float
    best_ask: float
    last_trade_price: float
    spread: float
    implied_probability: float
    opportunity_score: float
    resolution_time: datetime | None
    metadata_json: dict


class MarketSnapshotRead(TimeStamped):
    id: int
    market_id: int
    observed_at: datetime
    best_bid: float
    best_ask: float
    last_trade_price: float
    spread: float
    liquidity: float
    volume: float
    implied_probability: float
    price_change_1h: float
    price_change_24h: float
    momentum_score: float
    opportunity_score: float
    metadata_json: dict


class ScannerRunResponse(BaseModel):
    message: str
    scanned_markets: int
    source: str
