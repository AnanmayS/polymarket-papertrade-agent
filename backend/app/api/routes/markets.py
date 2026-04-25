"""Market routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.market_repository import MarketRepository
from app.schemas.market import MarketRead

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/active", response_model=list[MarketRead])
def get_active_markets(db: Session = Depends(get_db)) -> list[MarketRead]:
    return MarketRepository(db).list_active_markets()


@router.get("/candidates", response_model=list[MarketRead])
def get_candidate_markets(db: Session = Depends(get_db)) -> list[MarketRead]:
    return MarketRepository(db).list_candidate_markets()
