"""Portfolio routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db), settings: Settings = Depends(get_app_settings)):
    return AnalyticsService(db, settings).snapshot()
