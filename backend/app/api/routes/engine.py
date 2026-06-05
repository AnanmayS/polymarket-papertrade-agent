"""Engine routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, require_engine_control
from app.core.config import Settings
from app.repositories.trade_repository import TradeRepository
from app.schemas.engine import EngineActionResponse, ManualSettleRequest
from app.services.engine_service import EngineService
from app.services.settlement_service import SettlementService

router = APIRouter(
    prefix="/engine",
    tags=["engine"],
    dependencies=[Depends(require_engine_control)],
)


@router.post("/run-scan", response_model=EngineActionResponse)
def run_scan(
    db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)
) -> EngineActionResponse:
    result = EngineService(db, settings).run_scan()
    return EngineActionResponse(
        message="Market scan completed",
        created=result.markets_scanned,
        notes=[f"source:{result.source}"],
    )


@router.post("/run-signals", response_model=EngineActionResponse)
def run_signals(
    db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)
) -> EngineActionResponse:
    signal_result, risk_result = EngineService(db, settings).run_signals()
    return EngineActionResponse(
        message="Signal and risk evaluation completed",
        created=signal_result.signals_created,
        notes=signal_result.notes + risk_result.notes,
    )


@router.post("/run-paper-trades", response_model=EngineActionResponse)
def run_paper_trades(
    db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)
) -> EngineActionResponse:
    result = EngineService(db, settings).run_paper_trades()
    return EngineActionResponse(
        message="Paper trades simulated", created=result.trades_created, notes=result.notes
    )


@router.post("/run-cycle", response_model=EngineActionResponse)
def run_cycle(
    db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)
) -> EngineActionResponse:
    result = EngineService(db, settings).run_cycle()
    return EngineActionResponse(
        message="Agent cycle completed",
        created=result["trades"].trades_created,
        notes=[
            f"scanned:{result['scan'].markets_scanned}",
            f"signals:{result['signals'].signals_created}",
            f"risk_checks:{result['risk'].decisions_created}",
            f"trades:{result['trades'].trades_created}",
            f"settled:{result['settlement'].settled_trades}",
        ],
    )


@router.post("/settle-paper-trades", response_model=EngineActionResponse)
def settle_paper_trades(
    db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)
) -> EngineActionResponse:
    result = EngineService(db, settings).settle_paper_trades()
    return EngineActionResponse(
        message="Paper trades settled", created=result.settled_trades, notes=result.notes
    )


@router.post("/manual-settle-trade/{trade_id}", response_model=EngineActionResponse)
def manual_settle_trade(
    trade_id: int,
    body: ManualSettleRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> EngineActionResponse:
    """Force-settle a trade with a manual YES/NO outcome.

    Use this when a market has disappeared from Polymarket's API
    or the automated settlement couldn't determine the outcome.
    """
    trade_repo = TradeRepository(db)
    trade = trade_repo.get_trade(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    if trade.status == "settled":
        return EngineActionResponse(
            message=f"Trade {trade_id} is already settled",
            created=0,
            notes=[f"trade:{trade_id}:already_settled"],
        )

    svc = SettlementService(db, settings)
    svc.settle_trade(trade_id, body.outcome_yes)
    db.commit()
    return EngineActionResponse(
        message=f"Trade {trade_id} settled as {'YES' if body.outcome_yes else 'NO'}",
        created=1,
        notes=[f"trade:{trade_id}:{'won' if body.outcome_yes else 'lost'}"],
    )


@router.post("/delete-trade/{trade_id}", response_model=EngineActionResponse)
def delete_trade(
    trade_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> EngineActionResponse:
    """Delete a stuck open trade and its position so the engine can re-bet on live markets."""
    repo = TradeRepository(db)
    trade = repo.get_trade(trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    if trade.status == "settled":
        return EngineActionResponse(
            message=f"Trade {trade_id} is already settled — won't delete settled trades",
            created=0,
            notes=[f"trade:{trade_id}:already_settled"],
        )

    repo.delete_trade_and_position(trade_id)
    db.commit()
    return EngineActionResponse(
        message=f"Trade {trade_id} deleted",
        created=0,
        notes=[f"trade:{trade_id}:deleted"],
    )
