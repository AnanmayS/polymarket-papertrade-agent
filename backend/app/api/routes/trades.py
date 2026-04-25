"""Trade routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.models.market import Market
from app.repositories.trade_repository import TradeRepository
from app.services.polymarket_client import PolymarketClient

router = APIRouter(tags=["trades"])


def _derive_event_slug(market: Market | None) -> str | None:
    if market is None:
        return None

    metadata = market.metadata_json or {}
    event_slug = metadata.get("event_slug")
    if event_slug:
        return str(event_slug)
    if str(metadata.get("sports_market_type") or "").lower() == "moneyline":
        return None
    return market.slug or None


def _market_url(market: Market | None) -> str | None:
    slug = _derive_event_slug(market)
    if not slug:
        return None
    return f"https://polymarket.com/event/{slug}"


def _backfill_event_slugs(
    db: Session,
    markets: dict[int, Market],
    settings: Settings,
) -> bool:
    unresolved = [
        market
        for market in markets.values()
        if market.external_id and not (market.metadata_json or {}).get("event_slug")
    ]
    if not unresolved:
        return False

    slug_map = PolymarketClient(settings).fetch_active_event_slug_map()
    if not slug_map:
        return False

    updated = False
    for market in unresolved:
        event_slug = slug_map.get(market.external_id)
        if not event_slug:
            continue
        metadata = dict(market.metadata_json or {})
        metadata["event_slug"] = event_slug
        market.metadata_json = metadata
        updated = True

    if updated:
        db.flush()
    return updated


@router.get("/trades")
def list_trades(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> list[dict]:
    trades = TradeRepository(db).list_trades()
    markets = {
        market.id: market
        for market in db.scalars(
            select(Market).where(Market.id.in_([trade.market_id for trade in trades]))
        )
    }
    if _backfill_event_slugs(db, markets, settings):
        db.commit()
    return [
        {
            "id": trade.id,
            "market_id": trade.market_id,
            "market_question": (
                markets[trade.market_id].question if trade.market_id in markets else ""
            ),
            "market_url": _market_url(markets.get(trade.market_id)),
            "status": trade.status,
            "side": trade.side,
            "stake": trade.stake,
            "quantity": trade.quantity,
            "fill_price": trade.fill_price,
            "exit_price": trade.exit_price,
            "fees_paid": trade.fees_paid,
            "slippage_paid": trade.slippage_paid,
            "realized_pnl": trade.realized_pnl,
            "unrealized_pnl": trade.unrealized_pnl,
            "confidence": trade.confidence,
            "entry_edge": trade.entry_edge,
            "rationale": trade.rationale,
            "opened_at": trade.opened_at,
            "settled_at": trade.settled_at,
        }
        for trade in trades
    ]


@router.get("/trades/{trade_id}")
def get_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict:
    trade = TradeRepository(db).get_trade(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    market = db.get(Market, trade.market_id)
    if market is not None:
        if _backfill_event_slugs(db, {market.id: market}, settings):
            db.commit()
    return {
        "id": trade.id,
        "market_id": trade.market_id,
        "market_question": market.question if market else "",
        "market_url": _market_url(market),
        "status": trade.status,
        "side": trade.side,
        "stake": trade.stake,
        "quantity": trade.quantity,
        "fill_price": trade.fill_price,
        "exit_price": trade.exit_price,
        "fees_paid": trade.fees_paid,
        "slippage_paid": trade.slippage_paid,
        "realized_pnl": trade.realized_pnl,
        "unrealized_pnl": trade.unrealized_pnl,
        "confidence": trade.confidence,
        "entry_edge": trade.entry_edge,
        "rationale": trade.rationale,
        "opened_at": trade.opened_at,
        "settled_at": trade.settled_at,
    }
