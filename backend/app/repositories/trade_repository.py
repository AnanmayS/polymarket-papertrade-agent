"""Trade persistence."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.portfolio import PortfolioSnapshot
from app.models.postmortem import Postmortem
from app.models.trade import Position, Trade


class TradeRepository:
    """Repository for trades, positions, and portfolio snapshots."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_trade(self, payload: dict) -> Trade:
        trade = Trade(**payload)
        self.session.add(trade)
        self.session.flush()
        return trade

    def list_trades(self, limit: int = 200) -> list[Trade]:
        stmt = select(Trade).order_by(desc(Trade.created_at)).limit(limit)
        return list(self.session.scalars(stmt))

    def get_trade(self, trade_id: int) -> Trade | None:
        return self.session.get(Trade, trade_id)

    def open_positions(self) -> list[Position]:
        stmt = select(Position).where(Position.status == "open").order_by(desc(Position.updated_at))
        return list(self.session.scalars(stmt))

    def get_position_by_market(self, market_id: int) -> Position | None:
        stmt = select(Position).where(Position.market_id == market_id)
        return self.session.scalar(stmt)

    def upsert_position(self, payload: dict) -> Position:
        position = self.get_position_by_market(payload["market_id"])
        if position is None:
            position = Position(**payload)
            self.session.add(position)
        else:
            for key, value in payload.items():
                setattr(position, key, value)
        self.session.flush()
        return position

    def create_portfolio_snapshot(self, payload: dict) -> PortfolioSnapshot:
        snapshot = PortfolioSnapshot(**payload)
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def list_portfolio_snapshots(self, limit: int = 200) -> list[PortfolioSnapshot]:
        stmt = select(PortfolioSnapshot).order_by(desc(PortfolioSnapshot.created_at)).limit(limit)
        return list(self.session.scalars(stmt))

    def create_postmortem(self, payload: dict) -> Postmortem:
        postmortem = Postmortem(**payload)
        self.session.add(postmortem)
        self.session.flush()
        return postmortem

    def get_postmortem_by_trade(self, trade_id: int) -> Postmortem | None:
        stmt = select(Postmortem).where(Postmortem.trade_id == trade_id)
        return self.session.scalar(stmt)

    def list_postmortems(self, limit: int = 100) -> list[Postmortem]:
        stmt = select(Postmortem).order_by(desc(Postmortem.created_at)).limit(limit)
        return list(self.session.scalars(stmt))
