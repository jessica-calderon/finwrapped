import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from app.core.config import settings
from app.services.jellyfin_client import JellyfinClient, create_client
from app.services.jellystat_client import JellystatClient
from app.services.playback_db import get_events as get_db_events
from app.services.time_ranges import ResolvedTimeWindow, resolve_time_window

logger = logging.getLogger(__name__)

_DATA_MODES = {"auto", "jellystat", "jellyfin", "sync"}


def get_playback_events(
    year: int | None = None,
    user_id: str | None = None,
    config: Mapping[str, Any] | None = None,
    range_key: str | None = None,
) -> list[dict[str, Any]]:
    resolved_config = _normalize_config(config)
    data_mode = resolved_config["dataMode"]
    resolved_window = resolve_time_window(year, range_key)

    logger.info("Data mode: %s", data_mode)

    if data_mode == "jellystat":
        logger.info("Using Jellystat only")
        return _load_events(resolved_window, user_id, resolved_config, source="jellystat")

    if data_mode == "jellyfin":
        logger.info("Using Jellyfin fallback")
        return _load_events(resolved_window, user_id, resolved_config, source="jellyfin")

    if data_mode == "sync":
        logger.info("Merging Jellystat + Jellyfin data")
        return merge_events(
            _load_events(resolved_window, user_id, resolved_config, source="jellystat"),
            _load_events(resolved_window, user_id, resolved_config, source="jellyfin"),
        )

    logger.info("Using auto mode")
    return _load_auto_events(resolved_window, user_id, resolved_config)


def merge_events(events_a: list[dict[str, Any]], events_b: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], dict[str, Any]] = {}

    for raw_event in [*events_a, *events_b]:
        event = _normalize_event(raw_event)
        if event is None:
            continue

        key = (
            event["user_id"] or "",
            event["item_name"] or "",
            event["played_at"].isoformat(),
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = event
            continue

        if not existing.get("duration") and event.get("duration"):
            existing["duration"] = event["duration"]

    return sorted(merged.values(), key=lambda item: item["played_at"])


def _load_auto_events(
    window: ResolvedTimeWindow,
    user_id: str | None,
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    jellystat_events = _load_events(window, user_id, config, source="jellystat")
    if jellystat_events:
        logger.info("Using Jellystat data")
        return jellystat_events

    logger.info("Jellystat returned no events, checking playback DB")
    return _load_events(window, user_id, config, source="jellyfin")


def _load_events(
    window: ResolvedTimeWindow,
    user_id: str | None,
    config: Mapping[str, Any],
    *,
    source: str,
) -> list[dict[str, Any]]:
    if source == "jellystat":
        return _fetch_jellystat_events(window, user_id, config)
    if source == "jellyfin":
        return _fetch_jellyfin_events(window, user_id, config)
    raise ValueError(f"Unknown data source: {source}")


def _fetch_jellystat_events(
    window: ResolvedTimeWindow,
    user_id: str | None,
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    jellystat_config = config.get("jellystat", {}) if isinstance(config, Mapping) else {}
    jellystat_url = _clean_text(jellystat_config.get("url"))
    jellystat_enabled = bool(jellystat_config.get("enabled")) and bool(jellystat_url)

    if not jellystat_enabled:
        return []

    events: list[dict[str, Any]] = []
    years = window.years

    try:
        client = JellystatClient(jellystat_url)
        if years is None:
            events.extend(_normalize_events(client.get_playback_events(None, user_id)))
        else:
            for current_year in years:
                events.extend(_normalize_events(client.get_playback_events(current_year, user_id)))
    except Exception as exc:  # noqa: BLE001 - fallback is intentional
        logger.warning("Jellystat data source failed: %s", exc)
        return []

    return _filter_events_to_window(events, window)


def _fetch_jellyfin_events(
    window: ResolvedTimeWindow,
    user_id: str | None,
    config: Mapping[str, Any],
) -> list[dict[str, Any]]:
    db_path = Path(settings.PLAYBACK_DB_PATH).expanduser() if settings.PLAYBACK_DB_PATH else None
    if db_path and db_path.exists():
        try:
            if window.years is None:
                db_events = _normalize_events(get_db_events(None, user_id))
            else:
                db_events = []
                for current_year in window.years:
                    db_events.extend(_normalize_events(get_db_events(current_year, user_id)))
        except Exception as exc:  # noqa: BLE001 - fallback is intentional
            logger.warning("Playback DB failed, falling back to Jellyfin API: %s", exc)
        else:
            filtered_db_events = _filter_events_to_window(db_events, window)
            if filtered_db_events:
                logger.info("Using playback DB")
                return filtered_db_events
            logger.info("Playback DB returned no events, falling back to Jellyfin API")
    else:
        logger.info("Playback DB missing, falling back to Jellyfin API")

    logger.info("Using Jellyfin fallback")
    jellyfin_client = _create_jellyfin_client(config)
    try:
        if window.years is None:
            events = _normalize_events(jellyfin_client.get_playback_events(None, user_id))
        else:
            events = []
            for current_year in window.years:
                events.extend(_normalize_events(jellyfin_client.get_playback_events(current_year, user_id)))
        return _filter_events_to_window(events, window)
    except Exception as exc:  # noqa: BLE001 - safe fallback
        logger.warning("Jellyfin API fallback failed: %s", exc)
        return []


def _create_jellyfin_client(config: Mapping[str, Any]) -> JellyfinClient:
    jellyfin_config = config.get("jellyfin", {}) if isinstance(config, Mapping) else {}
    return create_client(
        _clean_text(jellyfin_config.get("url")),
        _clean_text(jellyfin_config.get("apiKey")),
    )


def _normalize_events(events: list[dict[str, Any]] | list[Any]) -> list[dict[str, Any]]:
    normalized_events: list[dict[str, Any]] = []
    for event in events:
        normalized_event = _normalize_event(event)
        if normalized_event is not None:
            normalized_events.append(normalized_event)
    return normalized_events


def _filter_events_to_window(events: list[dict[str, Any]], window: ResolvedTimeWindow) -> list[dict[str, Any]]:
    if window.start is None and window.end is None:
        return sorted(events, key=lambda item: item["played_at"])

    filtered: list[dict[str, Any]] = []
    for event in events:
        played_at = event.get("played_at")
        if not isinstance(played_at, datetime):
            continue
        if window.start is not None and played_at < window.start:
            continue
        if window.end is not None and played_at >= window.end:
            continue
        filtered.append(event)

    filtered.sort(key=lambda item: item["played_at"])
    return filtered


def _normalize_event(event: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    played_at = _parse_timestamp(
        _safe_get(event, "played_at")
        or _safe_get(event, "playedAt")
        or _safe_get(event, "DatePlayed")
        or _safe_get(event, "datePlayed")
        or _safe_get(event, "timestamp")
        or _safe_get(event, "createdAt")
        or _safe_get(event, "created_at")
        or _safe_get(event, "LastPlayedDate")
        or _safe_get(event, "PlayedDate")
    )
    if not played_at:
        return None

    item_name = _clean_text(
        _safe_get(event, "item_name")
        or _safe_get(event, "itemName")
        or _safe_get(event, "ItemName")
        or _safe_get(event, "title")
        or _safe_get(event, "Title")
        or _safe_get(event, "name")
        or _safe_get(event, "Name")
        or _safe_get(event, "series_name")
        or _safe_get(event, "seriesName")
        or _safe_get(event, "SeriesName")
    )
    if not item_name:
        item_name = "Unknown title"

    item_type = _normalize_item_type(
        _safe_get(event, "item_type")
        or _safe_get(event, "itemType")
        or _safe_get(event, "ItemType")
        or _safe_get(event, "type")
        or _safe_get(event, "Type"),
        item_name,
    )

    user_id = _clean_text(
        _safe_get(event, "user_id")
        or _safe_get(event, "userId")
        or _safe_get(event, "UserId")
        or _safe_get(event, "user")
        or _safe_get(event, "User")
    )

    return {
        "user_id": user_id,
        "item_name": item_name,
        "item_type": item_type,
        "played_at": played_at,
        "duration": int(round(
            _coerce_duration_seconds(
                _safe_get(event, "duration")
                or _safe_get(event, "Duration")
                or _safe_get(event, "duration_seconds")
                or _safe_get(event, "durationSeconds")
                or _safe_get(event, "RunTimeTicks")
                or _safe_get(event, "RuntimeTicks")
                or _safe_get(event, "Runtime")
            )
        )),
    }


def _normalize_config(config: Mapping[str, Any] | None) -> dict[str, dict[str, Any] | str]:
    if not isinstance(config, Mapping):
        return {
            "jellyfin": {"url": "", "apiKey": ""},
            "jellystat": {"url": "", "enabled": False},
            "dataMode": "auto",
        }

    jellyfin_config = config.get("jellyfin", {})
    jellystat_config = config.get("jellystat", {})
    return {
        "jellyfin": {
            "url": _clean_text(_safe_get(jellyfin_config, "url")) or "",
            "apiKey": _clean_text(_safe_get(jellyfin_config, "apiKey")) or "",
        },
        "jellystat": {
            "url": _clean_text(_safe_get(jellystat_config, "url")) or "",
            "enabled": bool(_safe_get(jellystat_config, "enabled")),
        },
        "dataMode": _normalize_data_mode(_safe_get(config, "dataMode")),
    }


def _normalize_data_mode(value: Any) -> str:
    normalized = _clean_text(value)
    normalized = normalized.lower() if normalized else ""
    return normalized if normalized in _DATA_MODES else "auto"


def _safe_get(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


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


def _normalize_item_type(raw_type: Any, item_name: str) -> str:
    normalized = _clean_text(raw_type)
    normalized = normalized.lower() if normalized else ""
    if normalized in {"movie", "feature", "video"}:
        return "movie"
    if normalized in {"episode", "episodeitem", "series", "show"}:
        return "episode"
    return "movie" if item_name else "episode"


def _coerce_duration_seconds(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric >= 1e17:
            return numeric / 10_000_000
        if numeric >= 1e14:
            return numeric / 1_000_000
        if numeric >= 1e11:
            return numeric / 1_000
        return numeric
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0
