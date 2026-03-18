import logging
from datetime import UTC, datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)


class JellystatClientError(RuntimeError):
    """Raised when Jellystat returns an unexpected response."""


class JellystatClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get_playback_events(self, year: int | None = None, user_id: str | None = None) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for path in ("/api/plays", "/api/history"):
            try:
                payload = self._request_json(path)
            except JellystatClientError as exc:
                logger.warning("Unable to fetch Jellystat playback data from %s: %s", path, exc)
                continue

            items = self._extract_items(payload)
            if not items:
                continue

            for item in items:
                events.extend(self._normalize_item(item, year, user_id))

            if events:
                break

        events.sort(key=lambda event: event["played_at"])
        return events

    def _request_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, timeout=self.timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise JellystatClientError(f"HTTP {response.status_code} for {path}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise JellystatClientError(f"Invalid JSON returned from {path}") from exc

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        if not isinstance(payload, dict):
            return []

        for key in ("Items", "items", "Results", "results", "Data", "data", "Plays", "plays", "History", "history", "Events", "events"):
            items = payload.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]

        return []

    def _normalize_item(self, item: dict[str, Any], year: int | None, user_id: str | None) -> list[dict[str, Any]]:
        played_at = self._parse_timestamp(
            item.get("played_at")
            or item.get("playedAt")
            or item.get("DatePlayed")
            or item.get("datePlayed")
            or item.get("timestamp")
            or item.get("createdAt")
            or item.get("created_at")
        )
        if not played_at or (year is not None and played_at.year != year):
            return []

        event_user_id = self._string_value(
            item.get("user_id")
            or item.get("userId")
            or item.get("UserId")
            or item.get("user")
            or item.get("User")
        )
        if user_id and event_user_id and event_user_id != user_id:
            return []

        item_name = self._string_value(
            item.get("item_name")
            or item.get("itemName")
            or item.get("ItemName")
            or item.get("title")
            or item.get("Title")
            or item.get("name")
            or item.get("Name")
            or item.get("series_name")
            or item.get("seriesName")
            or item.get("SeriesName")
        )
        if not item_name:
            item_name = "Unknown title"

        raw_type = self._string_value(item.get("item_type") or item.get("itemType") or item.get("ItemType") or item.get("type") or item.get("Type"))
        item_type = self._normalize_item_type(raw_type, item_name)
        duration = int(round(self._coerce_duration_seconds(item.get("duration") or item.get("Duration") or item.get("duration_seconds") or item.get("durationSeconds") or item.get("RunTimeTicks") or item.get("RuntimeTicks") or item.get("Runtime"))))
        play_count = max(1, self._coerce_int(item.get("play_count") or item.get("playCount") or item.get("Count") or item.get("count") or 1))

        resolved_user_id = event_user_id or user_id
        return [
            {
                "user_id": resolved_user_id,
                "item_name": item_name,
                "item_type": item_type,
                "played_at": played_at,
                "duration": duration,
            }
            for _ in range(play_count)
        ]

    def _parse_timestamp(self, value: Any) -> datetime | None:
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

    def _normalize_item_type(self, raw_type: str | None, item_name: str) -> str:
        normalized = (raw_type or "").strip().lower()
        if normalized in {"movie", "feature", "video"}:
            return "movie"
        if normalized in {"episode", "episodeitem", "series", "show"}:
            return "episode"
        return "movie" if item_name else "episode"

    def _coerce_duration_seconds(self, value: Any) -> float:
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

    def _coerce_int(self, value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    def _string_value(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


def create_client(base_url: str) -> JellystatClient:
    return JellystatClient(base_url)
