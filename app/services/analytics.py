import calendar
import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Mapping

from app.services.data_source import get_playback_events as get_source_playback_events
from app.services.time_ranges import ResolvedTimeWindow, format_time_range_label, resolve_time_window

logger = logging.getLogger(__name__)

_BINGE_GAP_MINUTES = 30
_TOP_LIMIT = 10


def get_basic_stats(
    year: int | None = None,
    user_id: str | None = None,
    config: Mapping[str, Any] | None = None,
    jellyfin_client: Any | None = None,
    range_key: str | None = None,
) -> dict[str, Any]:
    """Backward-compatible entrypoint used by the current routes."""

    return build_recap(year, user_id, config, jellyfin_client, range_key)


def build_recap(
    year: int | None = None,
    user_id: str | None = None,
    config: Mapping[str, Any] | None = None,
    jellyfin_client: Any | None = None,
    range_key: str | None = None,
) -> dict[str, Any]:
    """Generate the recap payload for a given time window and optional user."""

    resolved_window = resolve_time_window(year, range_key)
    events = _load_playback_events(resolved_window, user_id, config, jellyfin_client)
    normalized_events = [
        event
        for event in (_normalize_event(item, resolved_window, user_id) for item in events)
        if event
    ]

    total_hours = round(
        sum(event["duration"] for event in normalized_events) / 3600,
        2,
    )

    return {
        "year": resolved_window.year,
        "range": resolved_window.key,
        "range_label": resolved_window.label,
        "user": user_id,
        "total_hours": total_hours,
        "top_movies": _top_items(normalized_events, kind="movie"),
        "top_shows": _top_items(normalized_events, kind="show"),
        "most_active_day": _most_active_day(normalized_events),
        "most_active_hour": _most_active_hour(normalized_events),
        "binge_sessions": _count_binge_sessions(normalized_events),
    }


def _load_playback_events(
    window: ResolvedTimeWindow,
    user_id: str | None,
    config: Mapping[str, Any] | None = None,
    jellyfin_client: Any | None = None,
) -> list[dict[str, Any]]:
    try:
        return get_source_playback_events(window.year, user_id, config, window.key)
    except Exception as exc:  # noqa: BLE001 - safe fallback
        logger.warning("Playback lookup failed: %s", exc)
        return []


def _normalize_event(
    item: Mapping[str, Any],
    window: ResolvedTimeWindow,
    user_id: str | None,
) -> dict[str, Any] | None:
    timestamp = _parse_timestamp(item.get("played_at") or item.get("timestamp"))
    if not timestamp:
        return None
    if window.start is not None and timestamp < window.start:
        return None
    if window.end is not None and timestamp >= window.end:
        return None

    event_user = _clean_text(item.get("user_id")) or user_id
    title = _clean_text(item.get("item_name") or item.get("title") or item.get("name")) or "Unknown title"
    item_type = _normalize_item_type(item.get("item_type"), title, None)
    duration_seconds = max(0, _coerce_int(item.get("duration") or item.get("duration_seconds") or 0))

    return {
        "played_at": timestamp,
        "user_id": event_user,
        "item_name": title,
        "item_type": item_type,
        "duration": duration_seconds,
    }


def _top_items(events: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()

    for event in events:
        if kind == "movie" and event["item_type"] != "movie":
            continue
        if kind == "show" and event["item_type"] != "episode":
            continue

        key = event["item_name"]
        if not key:
            continue
        counts[key] += 1

    items = sorted(counts.items(), key=lambda entry: (-entry[1], entry[0].lower()))
    return [{"title": title, "play_count": play_count} for title, play_count in items[:_TOP_LIMIT]]


def _most_active_day(events: list[dict[str, Any]]) -> str:
    counts: Counter[int] = Counter()
    for event in events:
        counts[event["played_at"].weekday()] += 1
    if not counts:
        return ""
    return calendar.day_name[counts.most_common(1)[0][0]]


def _most_active_hour(events: list[dict[str, Any]]) -> int:
    counts: Counter[int] = Counter()
    for event in events:
        counts[event["played_at"].hour] += 1
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

    for event in sorted(events, key=lambda entry: entry["played_at"]):
        timestamp = event["played_at"]
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
    if normalized in {"episode", "episodeitem", "series", "show"}:
        return "episode"
    if series_title and title and series_title != title:
        return "episode"
    if series_title and not title:
        return "episode"
    return "movie" if title else "episode"


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


def get_time_range_label(year: int | None = None, range_key: str | None = None) -> str:
    return format_time_range_label(year, range_key)