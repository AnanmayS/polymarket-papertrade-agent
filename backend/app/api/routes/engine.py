"""Engine routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db, require_engine_control
from app.core.config import Settings
from app.schemas.engine import EngineActionResponse
from app.services.engine_service import EngineService

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
