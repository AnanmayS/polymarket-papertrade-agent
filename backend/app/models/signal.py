"""Signal model."""

from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Signal(TimestampMixin, Base):
    """Trade signal generated from market features and a probability model."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    model_run_id: Mapped[int | None] = mapped_column(ForeignKey("model_runs.id"), nullable=True)
    mode: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="candidate")
    features_json: Mapped[dict] = mapped_column(JSON, default=dict)
    feature_importance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    market_probability: Mapped[float] = mapped_column(Float, default=0.0)
    fair_probability: Mapped[float] = mapped_column(Float, default=0.0)
    edge: Mapped[float] = mapped_column(Float, default=0.0)
    expected_value_proxy: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    rationale: Mapped[str] = mapped_column(Text)
