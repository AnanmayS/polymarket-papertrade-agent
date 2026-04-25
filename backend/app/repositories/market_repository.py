"""Market persistence helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.market import Market, MarketSnapshot


class MarketRepository:
    """Repository for market and snapshot reads/writes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_market(self, payload: dict) -> Market:
        market = self.session.scalar(
            select(Market).where(Market.external_id == payload["external_id"])
        )
        if market is None:
            market = Market(**payload)
            self.session.add(market)
        else:
            for key, value in payload.items():
                setattr(market, key, value)
        self.session.flush()
        return market

    def create_snapshot(self, payload: dict) -> MarketSnapshot:
        snapshot = MarketSnapshot(**payload)
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def deactivate_active_markets(self) -> None:
        for market in self.session.scalars(select(Market).where(Market.active.is_(True))):
            market.active = False
        self.session.flush()

    def list_active_markets(self, limit: int = 100) -> list[Market]:
        stmt = (
            select(Market)
            .where(Market.active.is_(True), Market.closed.is_(False), Market.archived.is_(False))
            .order_by(desc(Market.opportunity_score), desc(Market.volume))
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def get_market(self, market_id: int) -> Market | None:
        return self.session.get(Market, market_id)

    def get_by_external_id(self, external_id: str) -> Market | None:
        return self.session.scalar(select(Market).where(Market.external_id == external_id))

    def list_candidate_markets(self, min_score: float = 0.0, limit: int = 50) -> list[Market]:
        stmt = (
            select(Market)
            .where(
                Market.opportunity_score >= min_score,
                Market.active.is_(True),
                Market.closed.is_(False),
                Market.archived.is_(False),
            )
            .order_by(desc(Market.opportunity_score), desc(Market.volume))
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def latest_snapshot(self, market_id: int) -> MarketSnapshot | None:
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.market_id == market_id)
            .order_by(desc(MarketSnapshot.observed_at))
            .limit(1)
        )
        return self.session.scalar(stmt)

    def snapshot_before(self, market_id: int, hours_ago: int) -> MarketSnapshot | None:
        cutoff = datetime.now(UTC) - timedelta(hours=hours_ago)
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.market_id == market_id, MarketSnapshot.observed_at <= cutoff)
            .order_by(desc(MarketSnapshot.observed_at))
            .limit(1)
        )
        return self.session.scalar(stmt)
