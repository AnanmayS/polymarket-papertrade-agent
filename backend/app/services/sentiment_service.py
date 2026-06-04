"""Sentiment context collection for sports markets.

This is intentionally provider-agnostic: live news/social APIs can be wired in by
implementing ``collect_context`` without changing signal or risk code.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.market import Market
from app.models.sentiment import SentimentSignal
from app.utils.math import clamp
from app.utils.time import utc_now


@dataclass
class SentimentContext:
    source_type: str
    source_text: str
    team: str | None = None
    player: str | None = None
    game: str | None = None


@dataclass
class SentimentAssessment:
    score: float
    reason: str
    items: list[SentimentSignal]


class SentimentService:
    """Collect and score market sentiment with a mockable provider interface."""

    POSITIVE_TERMS = {
        "healthy": 0.18,
        "return": 0.15,
        "returns": 0.15,
        "lineup boost": 0.2,
        "rested": 0.12,
        "momentum": 0.1,
        "starter": 0.08,
        "confirmed": 0.08,
    }
    NEGATIVE_TERMS = {
        "injury": -0.25,
        "injured": -0.25,
        "out": -0.22,
        "questionable": -0.14,
        "doubtful": -0.2,
        "illness": -0.14,
        "limited": -0.1,
        "suspended": -0.25,
        "fatigue": -0.12,
        "public fade": -0.08,
    }

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def assess_market(self, market: Market) -> SentimentAssessment:
        contexts = self.collect_context(market)
        rows: list[SentimentSignal] = []
        scores: list[float] = []
        for context in contexts:
            score, reason = self.score_text(context.source_text)
            row = SentimentSignal(
                market_id=market.id,
                source_type=context.source_type,
                source_text=context.source_text,
                sentiment_score=score,
                reason=reason,
                observed_at=utc_now(),
                team=context.team,
                player=context.player,
                game=context.game or market.event_title,
            )
            self.session.add(row)
            self.session.flush()
            rows.append(row)
            scores.append(score)

        aggregate = clamp(sum(scores) / len(scores), -1.0, 1.0) if scores else 0.0
        reason = (
            f"Sentiment aggregate from {len(rows)} context item(s): {aggregate:+.2f}."
            if rows
            else "No sentiment context available; using neutral score."
        )
        return SentimentAssessment(score=aggregate, reason=reason, items=rows)

    def collect_context(self, market: Market) -> list[SentimentContext]:
        metadata = market.metadata_json or {}
        raw_items = metadata.get("sentiment_items")
        if isinstance(raw_items, list):
            return [
                SentimentContext(
                    source_type=str(item.get("source_type") or "mock"),
                    source_text=str(item.get("source_text") or item.get("headline") or ""),
                    team=item.get("team"),
                    player=item.get("player"),
                    game=item.get("game") or market.event_title,
                )
                for item in raw_items
                if isinstance(item, dict) and (item.get("source_text") or item.get("headline"))
            ]

        if not self.settings.sentiment_enabled:
            return []

        return [
            SentimentContext(
                source_type="mock",
                source_text=(
                    f"No live sentiment provider configured for {market.event_title or market.question}."
                ),
                team=market.outcome_name,
                game=market.event_title,
            )
        ]

    def score_text(self, text: str) -> tuple[float, str]:
        lowered = text.lower()
        score = 0.0
        matched: list[str] = []
        for term, weight in self.POSITIVE_TERMS.items():
            if term in lowered:
                score += weight
                matched.append(term)
        for term, weight in self.NEGATIVE_TERMS.items():
            if term in lowered:
                score += weight
                matched.append(term)

        score = clamp(score, -1.0, 1.0)
        reason = (
            f"Matched sentiment terms: {', '.join(matched)}."
            if matched
            else "No injury, lineup, momentum, or public-bias keywords found."
        )
        return score, reason
