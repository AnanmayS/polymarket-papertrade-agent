"""Postmortem schemas."""

from app.schemas.common import TimeStamped


class PostmortemRead(TimeStamped):
    id: int
    trade_id: int
    market_id: int
    entry_fair_probability: float
    market_probability_at_entry: float
    final_result: str
    pnl: float
    sizing_assessment: str
    feature_drivers_json: dict
    lessons_learned: str
    summary: str
