"""Signal schemas."""

from app.schemas.common import TimeStamped


class SignalRead(TimeStamped):
    id: int
    market_id: int
    model_run_id: int | None
    mode: str
    status: str
    features_json: dict
    feature_importance_json: dict
    market_probability: float
    fair_probability: float
    edge: float
    expected_value_proxy: float
    confidence: float
    opportunity_score: float
    rationale: str


class RiskDecisionRead(TimeStamped):
    id: int
    market_id: int
    signal_id: int
    approved: bool
    reason_codes: list[str]
    bankroll_before: float
    proposed_stake: float
    confidence: float
    details_json: dict
