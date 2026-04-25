"""Risk decisions."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RiskDecision(TimestampMixin, Base):
    """Approval or rejection emitted by the risk engine."""

    __tablename__ = "risk_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id"), index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), index=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    bankroll_before: Mapped[float] = mapped_column(Float, default=0.0)
    proposed_stake: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    details_json: Mapped[dict] = mapped_column(JSON, default=dict)
