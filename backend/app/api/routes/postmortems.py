"""Postmortem routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.market import Market
from app.repositories.trade_repository import TradeRepository

router = APIRouter(tags=["postmortems"])


@router.get("/postmortems")
def list_postmortems(db: Session = Depends(get_db)) -> list[dict]:
    postmortems = TradeRepository(db).list_postmortems()
    markets = {
        market.id: market
        for market in db.scalars(
            select(Market).where(
                Market.id.in_([postmortem.market_id for postmortem in postmortems])
            )
        )
    }
    return [
        {
            "id": postmortem.id,
            "trade_id": postmortem.trade_id,
            "market_id": postmortem.market_id,
            "market_question": (
                markets[postmortem.market_id].question if postmortem.market_id in markets else ""
            ),
            "final_result": postmortem.final_result,
            "pnl": postmortem.pnl,
            "sizing_assessment": postmortem.sizing_assessment,
            "lessons_learned": postmortem.lessons_learned,
            "summary": postmortem.summary,
            "feature_drivers_json": postmortem.feature_drivers_json,
            "created_at": postmortem.created_at,
        }
        for postmortem in postmortems
    ]
