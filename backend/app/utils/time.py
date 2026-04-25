"""Time helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Coerce a datetime into a UTC-aware value for database portability."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def local_now(timezone_name: str) -> datetime:
    """Return the current time in a configured local timezone."""

    return utc_now().astimezone(ZoneInfo(timezone_name))


def to_local(value: datetime | None, timezone_name: str) -> datetime | None:
    """Convert a datetime to the configured local timezone."""

    if value is None:
        return None
    return ensure_utc(value).astimezone(ZoneInfo(timezone_name))
