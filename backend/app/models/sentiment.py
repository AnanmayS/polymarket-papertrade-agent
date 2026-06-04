"""Transparent sentiment inputs connected to markets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SentimentSignal(TimestampMixin, Base):
    """One news/social/context item used by the bet scoring pipeline."""

    __tablename__ = "sentiment_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(64), default="mock")
    source_text: Mapped[str] = mapped_column(Text)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    team: Mapped[str | None] = mapped_column(String(128), nullable=True)
    player: Mapped[str | None] = mapped_column(String(128), nullable=True)
    game: Mapped[str | None] = mapped_column(String(256), nullable=True)
