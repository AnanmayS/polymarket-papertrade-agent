"""Signal routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.market import Market
from app.models.risk import RiskDecision
from app.models.signal import Signal

router = APIRouter(tags=["signals"])


@router.get("/signals")
def get_signals(db: Session = Depends(get_db)) -> list[dict]:
    signals = list(db.scalars(select(Signal).order_by(desc(Signal.created_at)).limit(200)))
    latest_by_market: dict[int, Signal] = {}
    for signal in signals:
        latest_by_market.setdefault(signal.market_id, signal)

    risk_map = {
        decision.signal_id: decision
        for decision in db.scalars(
            select(RiskDecision).order_by(desc(RiskDecision.created_at)).limit(100)
        )
    }
    markets = {
        market.id: market
        for market in db.scalars(select(Market).where(Market.id.in_(list(latest_by_market.keys()))))
    }
    return [
        {
            "id": signal.id,
            "market_id": signal.market_id,
            "market_question": (
                markets[signal.market_id].question if signal.market_id in markets else ""
            ),
            "event_title": (
                markets[signal.market_id].event_title if signal.market_id in markets else ""
            ),
            "mode": signal.mode,
            "status": signal.status,
            "market_probability": signal.market_probability,
            "fair_probability": signal.fair_probability,
            "edge": signal.edge,
            "expected_value_proxy": signal.expected_value_proxy,
            "confidence": signal.confidence,
            "opportunity_score": signal.opportunity_score,
            "rationale": signal.rationale,
            "features": signal.features_json,
            "feature_importance": signal.feature_importance_json,
            "risk": (
                {
                    "approved": risk_map[signal.id].approved,
                    "reason_codes": risk_map[signal.id].reason_codes,
                    "proposed_stake": risk_map[signal.id].proposed_stake,
                }
                if signal.id in risk_map
                else None
            ),
            "created_at": signal.created_at,
        }
        for signal in latest_by_market.values()
    ]
