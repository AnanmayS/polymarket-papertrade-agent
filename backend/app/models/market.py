"""Market models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Market(TimestampMixin, Base):
    """Prediction market tracked by the scanner."""

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), default="sports", index=True)
    subcategory: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sports_league: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    outcome_name: Mapped[str] = mapped_column(String(64), default="YES")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    closed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    liquidity: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    best_bid: Mapped[float] = mapped_column(Float, default=0.0)
    best_ask: Mapped[float] = mapped_column(Float, default=0.0)
    last_trade_price: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    implied_probability: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    resolution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    snapshots: Mapped[list[MarketSnapshot]] = relationship(back_populates="market")


class MarketSnapshot(TimestampMixin, Base):
    """Point-in-time market metrics used for signals and analytics."""

    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    best_bid: Mapped[float] = mapped_column(Float, default=0.0)
    best_ask: Mapped[float] = mapped_column(Float, default=0.0)
    last_trade_price: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    liquidity: Mapped[float] = mapped_column(Float, default=0.0)
    volume: Mapped[float] = mapped_column(Float, default=0.0)
    implied_probability: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_1h: Mapped[float] = mapped_column(Float, default=0.0)
    price_change_24h: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    market: Mapped[Market] = relationship(back_populates="snapshots")
