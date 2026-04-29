"""Public Polymarket API client with demo-data fallback support."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.utils.math import midpoint_probability
from app.utils.time import local_now

logger = get_logger(__name__)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes"}
    return default


def _parse_time(value: Any):
    if not value:
        return None
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None


def _parse_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
    return []


class PolymarketClient:
    """Fetch sports markets from public Polymarket endpoints."""

    SPORTS_TAG_ID = "1"
    GENERIC_TAG_SLUGS = {"sports", "games"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def load_demo_markets(self) -> list[dict[str, Any]]:
        demo_path = Path(__file__).resolve().parents[1] / "data" / "demo_markets.json"
        with demo_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(payload["markets"]):
            resolution_time = _parse_time(item.get("resolution_time"))
            resolution_time = self._shift_demo_resolution_time(resolution_time, index)
            normalized.append(
                {
                    **item,
                    "resolution_time": resolution_time,
                    "metadata_json": item.get("metadata_json", {}),
                }
            )
        return normalized

    def _shift_demo_resolution_time(
        self, resolution_time: datetime | None, index: int
    ) -> datetime | None:
        """Move demo events into the next few local days so demo scans stay stable."""

        if resolution_time is None:
            return None

        local_current_time = local_now(self.settings.market_timezone)
        days_ahead = min(index + 1, max(self.settings.resolution_window_days, 1))
        candidate_local_time = (local_current_time + timedelta(days=days_ahead)).replace(
            hour=19 if index % 2 == 0 else 20,
            minute=30 if index % 3 == 0 else 0,
            second=0,
            microsecond=0,
        )

        return candidate_local_time.astimezone(
            resolution_time.tzinfo or candidate_local_time.tzinfo
        )

    def fetch_active_sports_markets(self) -> tuple[list[dict[str, Any]], str]:
        """Fetch live sports markets from the sports events feed."""

        if not self.settings.use_live_polymarket_data:
            return self.load_demo_markets(), "demo"

        page_size = min(max(self.settings.scanner_limit * 5, 250), 500)
        max_pages = 4
        collected: list[dict[str, Any]] = []
        url = f"{self.settings.polymarket_gamma_url}/events"
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                for page in range(max_pages):
                    params = {
                        "tag_id": self.SPORTS_TAG_ID,
                        "related_tags": "true",
                        "active": "true",
                        "closed": "false",
                        "limit": str(page_size),
                        "offset": str(page * page_size),
                    }
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    raw_events = response.json()
                    if not isinstance(raw_events, list):
                        raise ValueError("Unexpected Gamma API payload")
                    if not raw_events:
                        break
                    for event in raw_events:
                        if not self._is_sports_event(event):
                            continue
                        for market in event.get("markets", []):
                            normalized = self.normalize_market(market, event)
                            if normalized is not None:
                                collected.append(normalized)
                return collected, "live"
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Live Polymarket fetch failed",
                extra={"extra_data": {"error": str(exc), "url": url}},
            )
            return [], "live"

    def fetch_active_event_slug_map(self) -> dict[str, str]:
        """Return a live market-id to event-slug map for active sports events."""

        if not self.settings.use_live_polymarket_data:
            return {}

        page_size = min(max(self.settings.scanner_limit * 5, 250), 500)
        max_pages = 4
        event_slug_map: dict[str, str] = {}
        url = f"{self.settings.polymarket_gamma_url}/events"
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                for page in range(max_pages):
                    params = {
                        "tag_id": self.SPORTS_TAG_ID,
                        "related_tags": "true",
                        "active": "true",
                        "closed": "false",
                        "limit": str(page_size),
                        "offset": str(page * page_size),
                    }
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    raw_events = response.json()
                    if not isinstance(raw_events, list):
                        raise ValueError("Unexpected Gamma API payload")
                    if not raw_events:
                        break
                    for event in raw_events:
                        if not self._is_sports_event(event):
                            continue
                        event_slug = str(event.get("slug") or "").strip()
                        if not event_slug:
                            continue
                        for market in event.get("markets", []):
                            external_id = (
                                market.get("id")
                                or market.get("conditionId")
                                or market.get("questionID")
                            )
                            if external_id:
                                event_slug_map[str(external_id)] = event_slug
                return event_slug_map
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Live event slug fetch failed",
                extra={"extra_data": {"error": str(exc), "url": url}},
            )
            return {}

    def fetch_market_by_id(self, external_id: str) -> dict[str, Any] | None:
        """Fetch the latest market state for one tracked live market."""

        if not external_id.isdigit():
            return None

        url = f"{self.settings.polymarket_gamma_url}/markets/{external_id}"
        try:
            with httpx.Client(timeout=self.settings.request_timeout_seconds) as client:
                response = client.get(url)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    return None
                return self.normalize_market(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Market refresh failed",
                extra={"extra_data": {"error": str(exc), "url": url, "market_id": external_id}},
            )
            return None

    def extract_resolved_outcome(self, item: dict[str, Any]) -> bool | None:
        """Infer the winning YES/NO side from resolved market data when possible."""

        metadata = item.get("metadata_json", {})
        demo_outcome = metadata.get("demo_final_outcome")
        if demo_outcome is not None:
            return bool(demo_outcome)

        outcomes = _parse_list(item.get("outcomes") or metadata.get("outcomes"))
        prices = [
            _as_float(price, -1.0)
            for price in _parse_list(
                item.get("outcomePrices")
                or item.get("outcome_prices")
                or metadata.get("outcomePrices")
                or metadata.get("outcome_prices")
            )
        ]
        if len(outcomes) < 2 or len(prices) < 2:
            return None

        first_label = str(outcomes[0]).strip().lower()
        second_label = str(outcomes[1]).strip().lower()
        first_price = prices[0]
        second_price = prices[1]

        if first_price >= 0.99:
            return first_label not in {"no", "false"}
        if second_price >= 0.99:
            return second_label in {"yes", "true"}
        return None

    def _is_sports_event(self, event: dict[str, Any]) -> bool:
        tags = event.get("tags", [])
        return any(
            str(tag.get("slug", "")).lower() == "sports" for tag in tags if isinstance(tag, dict)
        )

    def _derive_sports_labels(self, event: dict[str, Any]) -> tuple[str | None, str | None]:
        tags = [tag for tag in event.get("tags", []) if isinstance(tag, dict)]
        labels = [str(tag.get("label", "")).strip() for tag in tags if tag.get("label")]
        slugs = [str(tag.get("slug", "")).strip().lower() for tag in tags if tag.get("slug")]

        specific_labels = [
            label
            for label, slug in zip(labels, slugs, strict=False)
            if slug not in self.GENERIC_TAG_SLUGS
        ]
        subcategory = specific_labels[0] if specific_labels else None
        sports_league = specific_labels[-1] if len(specific_labels) > 1 else subcategory
        return subcategory, sports_league

    def normalize_market(
        self, item: dict[str, Any], event: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Normalize flexible API fields into the internal scanner payload."""

        subcategory, sports_league = self._derive_sports_labels(event or {})
        sports_market_type = item.get("sportsMarketTypeV2") or item.get("sportsMarketType")
        if event is not None and not sports_market_type:
            return None
        best_bid = _as_float(item.get("bestBid") or item.get("best_bid"))
        best_ask = _as_float(item.get("bestAsk") or item.get("best_ask"))
        last_trade_price = _as_float(item.get("lastTradePrice") or item.get("last_trade_price"))
        implied_probability = midpoint_probability(best_bid, best_ask, last_trade_price)
        external_id = item.get("id") or item.get("conditionId") or item.get("questionID")
        if not external_id:
            return None
        return {
            "external_id": str(external_id),
            "slug": item.get("slug") or f"market-{item.get('id')}",
            "question": item.get("question") or item.get("title") or "Unknown market",
            "category": "sports",
            "subcategory": subcategory,
            "sports_league": item.get("sportsLeague")
            or item.get("league")
            or item.get("sports_league")
            or sports_league,
            "event_title": item.get("eventTitle")
            or item.get("event_title")
            or (event.get("title") if event else None)
            or item.get("title"),
            "outcome_name": item.get("outcome") or "YES",
            "active": _as_bool(item.get("active"), True),
            "closed": _as_bool(item.get("closed"), False),
            "archived": _as_bool(item.get("archived"), False),
            "liquidity": _as_float(item.get("liquidityNum") or item.get("liquidity")),
            "volume": _as_float(item.get("volumeNum") or item.get("volume")),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "last_trade_price": last_trade_price or implied_probability,
            "spread": _as_float(item.get("spread"), max(best_ask - best_bid, 0.0)),
            "implied_probability": implied_probability,
            "opportunity_score": 0.0,
            "resolution_time": _parse_time(
                item.get("endDate")
                or item.get("resolveDate")
                or item.get("resolution_time")
                or item.get("end_date_iso")
                or (event.get("endDate") if event else None)
            ),
            "metadata_json": {
                "source": item.get("source", "gamma-events"),
                "sports_market_type": sports_market_type,
                "game_id": item.get("gameId"),
                "event_id": item.get("eventId") or (event.get("id") if event else None),
                "event_slug": event.get("slug") if event else None,
                "outcomes": _parse_list(item.get("outcomes")),
                "outcome_prices": _parse_list(item.get("outcomePrices")),
                "uma_resolution_statuses": item.get("umaResolutionStatuses"),
                "tags": event.get("tags", []) if event else [],
                "demo_final_outcome": (
                    item.get("metadata_json", {}).get("demo_final_outcome")
                    if isinstance(item.get("metadata_json"), dict)
                    else item.get("demo_final_outcome")
                ),
            },
        }
