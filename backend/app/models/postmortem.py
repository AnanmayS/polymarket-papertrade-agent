"""Postmortem records."""

from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Postmortem(TimestampMixin, Base):
    """Structured review of a settled paper trade."""

    __tablename__ = "postmortems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trade_id: Mapped[int] = mapped_column(ForeignKey("trades.id"), unique=True, index=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    entry_fair_probability: Mapped[float] = mapped_column(Float, default=0.0)
    market_probability_at_entry: Mapped[float] = mapped_column(Float, default=0.0)
    final_result: Mapped[str] = mapped_column(String(64))
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    sizing_assessment: Mapped[str] = mapped_column(Text)
    feature_drivers_json: Mapped[dict] = mapped_column(JSON, default=dict)
    lessons_learned: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
