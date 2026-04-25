"""Market scanning and ranking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.repositories.market_repository import MarketRepository
from app.services.polymarket_client import PolymarketClient
from app.utils.math import clamp
from app.utils.time import ensure_utc, local_now, to_local, utc_now


@dataclass
class ScanResult:
    markets_scanned: int
    source: str


class ScannerService:
    """Scan sports markets and persist snapshots."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = MarketRepository(session)
        self.client = PolymarketClient(settings)

    def run(self) -> ScanResult:
        raw_markets, source = self.client.fetch_active_sports_markets()
        self.repo.deactivate_active_markets()
        scanned = self._persist_markets(raw_markets, source)
        self.session.commit()
        return ScanResult(markets_scanned=scanned, source=source)

    def _persist_markets(self, raw_markets: list[dict], source: str) -> int:
        scanned = 0
        for payload in raw_markets:
            if not self._passes_filters(payload):
                continue
            market = self.repo.upsert_market(
                {**payload, "opportunity_score": self._opportunity_score(payload)}
            )
            previous_1h = self.repo.snapshot_before(market.id, 1)
            previous_24h = self.repo.snapshot_before(market.id, 24)
            current_price = payload["implied_probability"]
            price_change_1h = (
                current_price - previous_1h.implied_probability if previous_1h else 0.0
            )
            price_change_24h = (
                current_price - previous_24h.implied_probability if previous_24h else 0.0
            )
            self.repo.create_snapshot(
                {
                    "market_id": market.id,
                    "observed_at": utc_now(),
                    "best_bid": payload["best_bid"],
                    "best_ask": payload["best_ask"],
                    "last_trade_price": payload["last_trade_price"],
                    "spread": payload["spread"],
                    "liquidity": payload["liquidity"],
                    "volume": payload["volume"],
                    "implied_probability": current_price,
                    "price_change_1h": price_change_1h,
                    "price_change_24h": price_change_24h,
                    "momentum_score": (price_change_1h * 0.7) + (price_change_24h * 0.3),
                    "opportunity_score": market.opportunity_score,
                    "metadata_json": {"source": source},
                }
            )
            scanned += 1
        return scanned

    def _passes_filters(self, market: dict) -> bool:
        resolution_time = ensure_utc(market.get("resolution_time"))
        hours_to_resolution = (
            (resolution_time - utc_now()).total_seconds() / 3600
            if resolution_time
            else self.settings.max_hours_to_resolution
        )
        local_resolution_time = to_local(resolution_time, self.settings.market_timezone)
        local_current_time = local_now(self.settings.market_timezone)
        resolves_within_window = (
            local_resolution_time is not None
            and local_current_time <= local_resolution_time
            and local_resolution_time
            <= local_current_time + timedelta(days=self.settings.resolution_window_days)
        )
        return all(
            [
                market["liquidity"] >= self.settings.min_liquidity,
                market["volume"] >= self.settings.min_volume,
                market["spread"] <= self.settings.max_spread,
                hours_to_resolution >= self.settings.min_hours_to_resolution,
                hours_to_resolution <= self.settings.max_hours_to_resolution,
                resolves_within_window,
                market["active"] and not market["closed"] and not market["archived"],
            ]
        )

    def _opportunity_score(self, market: dict) -> float:
        volume_score = clamp(market["volume"] / max(self.settings.min_volume * 5, 1.0), 0.0, 1.0)
        liquidity_score = clamp(
            market["liquidity"] / max(self.settings.min_liquidity * 4, 1.0), 0.0, 1.0
        )
        spread_score = 1.0 - clamp(market["spread"] / max(self.settings.max_spread, 0.01), 0.0, 1.0)
        conviction_bonus = abs(market["implied_probability"] - 0.5) * 2
        return round(
            (volume_score * 0.35)
            + (liquidity_score * 0.35)
            + (spread_score * 0.2)
            + (conviction_bonus * 0.1),
            4,
        )
