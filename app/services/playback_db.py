import logging
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_TABLE_CANDIDATES = (
    "PlaybackActivity",
    "playback_activity",
    "PlaybackEvents",
    "playback_events",
    "PlaybackReporting",
    "playback_reporting",
    "Report",
    "Reports",
)

_TIMESTAMP_COLUMNS = (
    "PlayedAt",
    "PlaybackTime",
    "EventTime",
    "Timestamp",
    "TimeStamp",
    "DatePlayed",
    "LastPlayedDate",
    "CreatedAt",
    "DateCreated",
    "StartTime",
    "RecordedAt",
)

_USER_COLUMNS = ("UserId", "UserID", "user_id", "User")
_TITLE_COLUMNS = ("ItemName", "Title", "Name", "EpisodeTitle", "ItemTitle")
_SERIES_COLUMNS = ("SeriesName", "ShowName", "ParentName", "ParentTitle")
_TYPE_COLUMNS = ("MediaType", "ItemType", "Type")
_DURATION_COLUMNS = ("Duration", "DurationSeconds", "WatchedSeconds", "PlayDuration", "Runtime", "RunTimeTicks", "RuntimeTicks", "DurationTicks")
_PLAYCOUNT_COLUMNS = ("PlayCount", "play_count", "Count")


def get_playback_events(year: int, user_id: str | None = None) -> list[dict[str, Any]]:
    """
    Read playback rows from the SQLite reporting database and normalize them.

    The Jellyfin reporting schema varies by plugin/version, so this function
    probes likely tables and columns instead of assuming one fixed layout.
    """

    if not settings.PLAYBACK_DB_PATH:
        return []

    db_path = Path(settings.PLAYBACK_DB_PATH).expanduser()
    if not db_path.exists():
        return []

    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
            connection.row_factory = sqlite3.Row
            return _collect_events(connection, year, user_id)
    except sqlite3.Error as exc:
        logger.warning("Unable to read playback database %s: %s", db_path, exc)
        return []


def _collect_events(connection: sqlite3.Connection, year: int, user_id: str | None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for table_name in _candidate_tables(connection):
        columns = _table_columns(connection, table_name)
        timestamp_column = _pick_column(columns, _TIMESTAMP_COLUMNS)
        if not timestamp_column:
            continue

        normalized_rows = _fetch_table_rows(connection, table_name, columns, timestamp_column, year, user_id)
        events.extend(normalized_rows)

    events.sort(key=lambda event: event["timestamp"])
    return events


def _candidate_tables(connection: sqlite3.Connection) -> list[str]:
    available = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    ordered = [table for table in _TABLE_CANDIDATES if table in available]
    if ordered:
        return ordered
    return sorted(available)


def _table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return [row[1] for row in rows]


def _pick_column(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    lookup = {column.lower(): column for column in columns}
    for candidate in candidates:
        column = lookup.get(candidate.lower())
        if column:
            return column
    return None


def _fetch_table_rows(
    connection: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    timestamp_column: str,
    year: int,
    user_id: str | None,
) -> list[dict[str, Any]]:
    user_column = _pick_column(columns, _USER_COLUMNS)
    title_column = _pick_column(columns, _TITLE_COLUMNS)
    series_column = _pick_column(columns, _SERIES_COLUMNS)
    type_column = _pick_column(columns, _TYPE_COLUMNS)
    duration_column = _pick_column(columns, _DURATION_COLUMNS)
    playcount_column = _pick_column(columns, _PLAYCOUNT_COLUMNS)

    if user_id and not user_column:
        return []

    select_columns = [timestamp_column]
    for column in (user_column, title_column, series_column, type_column, duration_column, playcount_column):
        if column and column not in select_columns:
            select_columns.append(column)

    quoted_columns = ", ".join(f'"{column}"' for column in select_columns)
    sql = f'SELECT {quoted_columns} FROM "{table_name}"'
    where_clauses: list[str] = []
    params: list[Any] = []

    sample_value = _sample_timestamp(connection, table_name, timestamp_column)
    window_clause, window_params, filterable = _year_window(timestamp_column, sample_value, year)
    if filterable:
        where_clauses.append(window_clause)
        params.extend(window_params)

    if user_id and user_column:
        where_clauses.append(f'"{user_column}" = ?')
        params.append(user_id)

    if where_clauses:
        sql = f"{sql} WHERE " + " AND ".join(where_clauses)

    rows = connection.execute(sql, params).fetchall()
    normalized: list[dict[str, Any]] = []

    for row in rows:
        event = _normalize_row(
            row,
            timestamp_column=timestamp_column,
            user_column=user_column,
            title_column=title_column,
            series_column=series_column,
            type_column=type_column,
            duration_column=duration_column,
            playcount_column=playcount_column,
            year=year,
            user_id=user_id,
        )
        if event:
            normalized.append(event)

    if filterable:
        return normalized

    # Some schemas store timestamps in formats that SQLite cannot filter directly.
    return [event for event in normalized if event["timestamp"].year == year]


def _sample_timestamp(connection: sqlite3.Connection, table_name: str, timestamp_column: str) -> Any:
    row = connection.execute(
        f'SELECT "{timestamp_column}" FROM "{table_name}" WHERE "{timestamp_column}" IS NOT NULL LIMIT 1'
    ).fetchone()
    if not row:
        return None
    return row[0]


def _year_window(column: str, sample_value: Any, year: int) -> tuple[str, list[Any], bool]:
    start = datetime(year, 1, 1, tzinfo=UTC)
    end = datetime(year + 1, 1, 1, tzinfo=UTC)

    if isinstance(sample_value, (int, float)):
        numeric = float(sample_value)
        if numeric >= 1e17:
            start_ticks = _unix_to_ticks(start)
            end_ticks = _unix_to_ticks(end)
            return f'"{column}" >= ? AND "{column}" < ?', [start_ticks, end_ticks], True
        if numeric >= 1e14:
            return f'"{column}" >= ? AND "{column}" < ?', [int(start.timestamp() * 1_000_000), int(end.timestamp() * 1_000_000)], True
        if numeric >= 1e11:
            return f'"{column}" >= ? AND "{column}" < ?', [int(start.timestamp() * 1_000), int(end.timestamp() * 1_000)], True
        return f'"{column}" >= ? AND "{column}" < ?', [int(start.timestamp()), int(end.timestamp())], True

    if isinstance(sample_value, str):
        return f'"{column}" >= ? AND "{column}" < ?', [start.isoformat(), end.isoformat()], True

    return "", [], False


def _normalize_row(
    row: sqlite3.Row,
    *,
    timestamp_column: str,
    user_column: str | None,
    title_column: str | None,
    series_column: str | None,
    type_column: str | None,
    duration_column: str | None,
    playcount_column: str | None,
    year: int,
    user_id: str | None,
) -> dict[str, Any] | None:
    timestamp = _parse_timestamp(row[timestamp_column])
    if not timestamp or timestamp.year != year:
        return None

    event_user_id = _string_value(row[user_column]) if user_column else user_id
    if user_id and event_user_id != user_id:
        return None

    title = _clean_text(_string_value(row[title_column]) if title_column else None)
    series_title = _clean_text(_string_value(row[series_column]) if series_column else None)
    media_type = _normalize_media_type(_string_value(row[type_column]) if type_column else None, title, series_title)
    duration_seconds = _coerce_duration_seconds(row[duration_column]) if duration_column else 0.0
    play_count = max(1, _coerce_int(row[playcount_column])) if playcount_column else 1

    resolved_title = title or series_title or "Unknown title"
    resolved_series = series_title if media_type == "episode" else None
    if media_type == "show":
        resolved_series = title or series_title or "Unknown show"
        resolved_title = resolved_series

    return {
        "timestamp": timestamp,
        "user_id": event_user_id,
        "title": resolved_title,
        "series_title": resolved_series,
        "item_type": media_type,
        "duration_seconds": duration_seconds,
        "play_count": play_count,
        "source": "sqlite",
    }


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


def _clean_text(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    return cleaned or None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).strip() or None


def _normalize_media_type(raw_type: str | None, title: str | None, series_title: str | None) -> str:
    normalized = (raw_type or "").strip().lower()
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


def _coerce_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


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


def _unix_to_ticks(value: datetime) -> int:
    return int((value.timestamp() * 10_000_000) + 621355968000000000)
