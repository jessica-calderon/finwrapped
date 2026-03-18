from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

SUPPORTED_TIME_RANGES: Final[dict[str, str]] = {
    "7d": "Last 7 days",
    "30d": "Last 30 days",
    "90d": "Last 3 months",
    "ytd": "This year",
    "1y": "Last year",
    "all": "All time",
}


@dataclass(frozen=True)
class ResolvedTimeWindow:
    key: str
    label: str
    start: datetime | None
    end: datetime | None
    years: tuple[int, ...] | None
    year: int | None


def normalize_time_range(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip().lower()
    return cleaned if cleaned in SUPPORTED_TIME_RANGES else None


def resolve_time_window(year: int | None = None, range_key: str | None = None) -> ResolvedTimeWindow:
    now = datetime.now(UTC)
    normalized_range = normalize_time_range(range_key)

    if normalized_range:
        start, end = _range_bounds(normalized_range, now)
        years = _years_for_window(start, end)
        return ResolvedTimeWindow(
            key=normalized_range,
            label=SUPPORTED_TIME_RANGES[normalized_range],
            start=start,
            end=end,
            years=years,
            year=year,
        )

    effective_year = year or now.year
    start = datetime(effective_year, 1, 1, tzinfo=UTC)
    end = datetime(effective_year + 1, 1, 1, tzinfo=UTC)
    return ResolvedTimeWindow(
        key=str(effective_year),
        label=str(effective_year),
        start=start,
        end=end,
        years=(effective_year,),
        year=effective_year,
    )


def format_time_range_label(year: int | None = None, range_key: str | None = None) -> str:
    resolved = resolve_time_window(year, range_key)
    return resolved.label


def _range_bounds(range_key: str, now: datetime) -> tuple[datetime | None, datetime | None]:
    if range_key == "7d":
        return now - timedelta(days=7), now
    if range_key == "30d":
        return now - timedelta(days=30), now
    if range_key == "90d":
        return now - timedelta(days=90), now
    if range_key == "ytd":
        return datetime(now.year, 1, 1, tzinfo=UTC), now
    if range_key == "1y":
        return now - timedelta(days=365), now
    if range_key == "all":
        return None, None
    return datetime(now.year, 1, 1, tzinfo=UTC), now


def _years_for_window(start: datetime | None, end: datetime | None) -> tuple[int, ...] | None:
    if start is None or end is None:
        return None

    return tuple(range(start.year, end.year + 1))
