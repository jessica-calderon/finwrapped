import calendar
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Mapping

from app.core.config import settings
from app.services.jellyfin_client import client
from app.services.playback_db import get_playback_events as get_db_playback_events

logger = logging.getLogger(__name__)

_BINGE_GAP_MINUTES = 30
_TOP_LIMIT = 10


def get_basic_stats(year: int, user_id: str | None = None) -> dict[str, Any]:
    """Backward-compatible entrypoint used by the current routes."""

    return build_recap(year, user_id)


def build_recap(year: int, user_id: str | None = None) -> dict[str, Any]:
    """Generate the recap payload for a given year and optional user."""

    events = _load_playback_events(year, user_id)
    normalized_events = [event for event in (_normalize_event(item, year, user_id) for item in events) if event]

    total_hours = round(
        sum(event["duration_seconds"] * event["play_count"] for event in normalized_events) / 3600,
        2,
    )

    return {
        "year": year,
        "user": user_id,
        "total_hours": total_hours,
        "top_movies": _top_items(normalized_events, kind="movie"),
        "top_shows": _top_items(normalized_events, kind="show"),
        "most_active_day": _most_active_day(normalized_events),
        "most_active_hour": _most_active_hour(normalized_events),
        "binge_sessions": _count_binge_sessions(normalized_events),
    }


def _load_playback_events(year: int, user_id: str | None) -> list[dict[str, Any]]:
    data_mode = settings.DATA_MODE.strip().lower()

    if data_mode == "hybrid":
        try:
            events = get_db_playback_events(year, user_id)
            if events:
                return events
        except Exception as exc:  # noqa: BLE001 - fallback is intentional
            logger.warning("SQLite playback lookup failed, falling back to API: %s", exc)

    try:
        return client.get_playback_activity(year, user_id)
    except Exception as exc:  # noqa: BLE001 - safe fallback
        logger.warning("Playback lookup failed: %s", exc)
        return []


def _normalize_event(item: Mapping[str, Any], year: int, user_id: str | None) -> dict[str, Any] | None:
    timestamp = _parse_timestamp(item.get("timestamp"))
    if not timestamp or timestamp.year != year:
        return None

    event_user = _clean_text(item.get("user_id")) or user_id
    title = _clean_text(item.get("title")) or "Unknown title"
    series_title = _clean_text(item.get("series_title"))
    item_type = _normalize_item_type(item.get("item_type"), title, series_title)
    duration_seconds = max(0.0, _coerce_float(item.get("duration_seconds")))
    play_count = max(1, _coerce_int(item.get("play_count") or 1))

    if item_type == "show":
        series_title = title or series_title or "Unknown show"
        title = series_title
    elif item_type == "episode":
        series_title = series_title or "Unknown show"
    else:
        series_title = None

    return {
        "timestamp": timestamp,
        "user_id": event_user,
        "title": title,
        "series_title": series_title,
        "item_type": item_type,
        "duration_seconds": duration_seconds,
        "play_count": play_count,
    }


def _top_items(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()

    for event in events:
        if kind == "movie" and event["item_type"] != "movie":
            continue
        if kind == "show" and event["item_type"] not in {"episode", "show"}:
            continue

        key = event["title"] if kind == "movie" else event["series_title"] or event["title"]
        if not key:
            continue
        counts[key] += event["play_count"]

    items = sorted(counts.items(), key=lambda entry: (-entry[1], entry[0].lower()))
    return [{"title": title, "play_count": play_count} for title, play_count in items[:_TOP_LIMIT]]


def _most_active_day(events: list[dict[str, Any]]) -> str:
    counts: Counter[int] = Counter()
    for event in events:
        counts[event["timestamp"].weekday()] += event["play_count"]
    if not counts:
        return ""
    return calendar.day_name[counts.most_common(1)[0][0]]


def _most_active_hour(events: list[dict[str, Any]]) -> int:
    counts: Counter[int] = Counter()
    for event in events:
        counts[event["timestamp"].hour] += event["play_count"]
    if not counts:
        return 0
    return counts.most_common(1)[0][0]


def _count_binge_sessions(events: list[dict[str, Any]]) -> int:
    if not events:
        return 0

    sessions = 0
    current_session: list[dict[str, Any]] = []
    previous_timestamp: datetime | None = None
    gap = _BINGE_GAP_MINUTES * 60

    for event in sorted(events, key=lambda entry: entry["timestamp"]):
        timestamp = event["timestamp"]
        if previous_timestamp is None or (timestamp - previous_timestamp).total_seconds() <= gap:
            current_session.append(event)
        else:
            if len(current_session) >= 2:
                sessions += 1
            current_session = [event]
        previous_timestamp = timestamp

    if len(current_session) >= 2:
        sessions += 1

    return sessions


def _normalize_item_type(raw_type: Any, title: str | None, series_title: str | None) -> str:
    normalized = str(raw_type or "").strip().lower()
    if normalized in {"movie", "feature", "video"}:
        return "movie"
    if normalized in {"episode", "episodeitem"}:
        return "episode"
    if normalized in {"series", "show"}:
        return "show"
    if series_title and title and series_title != title:
        return "episode"
    if series_title and not title:
        return "show"
    return "movie" if title else "unknown"


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric >= 1e17:
            unix_seconds = (numeric - 621355968000000000) / 10_000_000
            return datetime.fromtimestamp(unix_seconds, tz=UTC)
        if numeric >= 1e14:
            return datetime.fromtimestamp(numeric / 1_000_000, tz=UTC)
        if numeric >= 1e11:
            return datetime.fromtimestamp(numeric / 1_000, tz=UTC)
        return datetime.fromtimestamp(numeric, tz=UTC)
    if isinstance(value, str):
        cleaned = value.strip().replace("Z", "+00:00")
        formats = (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S.%f%z",
            "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        )
        for fmt in formats:
            try:
                parsed = datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0