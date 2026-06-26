"""Post-trade analysis routes."""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.services.post_trade_analysis_service import PostTradeAnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/strategy-performance")
def get_strategy_performance(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    return PostTradeAnalysisService(db, settings).strategy_performance()


@router.get("/temporal-patterns")
def get_temporal_patterns(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    return PostTradeAnalysisService(db, settings).temporal_patterns()


@router.get("/microstructure")
def get_microstructure(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    return PostTradeAnalysisService(db, settings).microstructure_analysis()


@router.get("/ab-comparison")
def get_ab_comparison(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    return PostTradeAnalysisService(db, settings).strategy_ab_comparison()


@router.get("/export-csv", response_class=PlainTextResponse)
def export_trades_csv(
    status: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """Export trade log as CSV for external analysis."""
    csv_content = PostTradeAnalysisService(db, settings).export_csv(status=status)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trade_log.csv"},
    )


@router.get("/all")
def get_all_analysis(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
):
    """Return all analysis results in a single response."""
    service = PostTradeAnalysisService(db, settings)
    return {
        "strategy_performance": service.strategy_performance(),
        "temporal_patterns": service.temporal_patterns(),
        "microstructure": service.microstructure_analysis(),
        "ab_comparison": service.strategy_ab_comparison(),
    }
