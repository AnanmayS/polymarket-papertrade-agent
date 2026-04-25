"""Signal persistence."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.model_run import ModelRun
from app.models.risk import RiskDecision
from app.models.signal import Signal


class SignalRepository:
    """Repository for signal and risk records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_model_run(self, payload: dict) -> ModelRun:
        model_run = ModelRun(**payload)
        self.session.add(model_run)
        self.session.flush()
        return model_run

    def create_signal(self, payload: dict) -> Signal:
        signal = Signal(**payload)
        self.session.add(signal)
        self.session.flush()
        return signal

    def create_risk_decision(self, payload: dict) -> RiskDecision:
        decision = RiskDecision(**payload)
        self.session.add(decision)
        self.session.flush()
        return decision

    def list_signals(self, limit: int = 100) -> list[Signal]:
        stmt = select(Signal).order_by(desc(Signal.created_at)).limit(limit)
        return list(self.session.scalars(stmt))

    def latest_approved_decisions(self, limit: int = 50) -> list[RiskDecision]:
        stmt = (
            select(RiskDecision)
            .where(RiskDecision.approved.is_(True))
            .order_by(desc(RiskDecision.created_at))
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def latest_signal_for_market(self, market_id: int) -> Signal | None:
        stmt = (
            select(Signal)
            .where(Signal.market_id == market_id)
            .order_by(desc(Signal.created_at))
            .limit(1)
        )
        return self.session.scalar(stmt)
