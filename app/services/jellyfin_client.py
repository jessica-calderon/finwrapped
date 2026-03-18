import logging
from datetime import UTC, datetime
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class JellyfinClientError(RuntimeError):
    """Raised when Jellyfin returns an unexpected error."""


class JellyfinClient:
    def __init__(self) -> None:
        self.base_url = settings.JELLYFIN_URL.rstrip("/")
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-Emby-Token": settings.API_KEY,
            }
        )

    def get_users(self) -> list[dict[str, Any]]:
        """Return Jellyfin users. Empty list is returned if the API fails."""

        try:
            payload = self._request_json("/Users")
        except JellyfinClientError as exc:
            logger.warning("Unable to fetch Jellyfin users: %s", exc)
            return []
        return payload if isinstance(payload, list) else payload.get("Items", [])

    def get_playback_activity(self, year: int, user_id: str | None = None, page_size: int = 200) -> list[dict[str, Any]]:
        """
        Return normalized playback-like records from the Jellyfin API.

        Jellyfin does not expose a universal historical playback endpoint in the
        core API, so this method uses watched items and last-played metadata as a
        best-effort fallback when the reporting database is unavailable.
        """

        users = [{"Id": user_id}] if user_id else self.get_users()
        events: list[dict[str, Any]] = []

        for user in users:
            current_user_id = user.get("Id") or user_id
            if not current_user_id:
                continue

            start_index = 0
            while True:
                try:
                    payload = self._request_json(
                        f"/Users/{current_user_id}/Items",
                        params={
                            "Recursive": "true",
                            "Filters": "IsPlayed",
                            "IncludeItemTypes": "Movie,Episode,Series",
                            "Fields": "RunTimeTicks,UserData,SeriesName,ParentId,ParentIndexNumber,IndexNumber",
                            "SortBy": "DatePlayed",
                            "SortOrder": "Descending",
                            "StartIndex": start_index,
                            "Limit": page_size,
                        },
                    )
                except JellyfinClientError as exc:
                    logger.warning("Unable to fetch playback items for user %s: %s", current_user_id, exc)
                    break

                items = payload if isinstance(payload, list) else payload.get("Items", [])
                if not items:
                    break

                for item in items:
                    events.extend(self._normalize_item(item, year, current_user_id))

                if len(items) < page_size:
                    break
                start_index += page_size

        events.sort(key=lambda event: event["timestamp"])
        return events

    def _request_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        response = self.session.get(url, params=params, timeout=self.timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise JellyfinClientError(f"HTTP {response.status_code} for {path}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise JellyfinClientError(f"Invalid JSON returned from {path}") from exc

    def _normalize_item(self, item: dict[str, Any], year: int, user_id: str) -> list[dict[str, Any]]:
        user_data = item.get("UserData") or {}
        timestamp = self._parse_timestamp(
            user_data.get("LastPlayedDate")
            or user_data.get("PlayedDate")
            or item.get("LastPlayedDate")
            or item.get("DatePlayed")
            or item.get("PremiereDate")
        )
        if not timestamp or timestamp.year != year:
            return []

        play_count = self._coerce_int(user_data.get("PlayCount") or item.get("PlayCount") or 1)
        play_count = max(1, play_count)
        duration_seconds = self._coerce_duration_seconds(item.get("RunTimeTicks") or item.get("RuntimeTicks") or item.get("Runtime"))

        title = self._clean_text(item.get("Name") or item.get("Title"))
        series_title = self._clean_text(item.get("SeriesName") or item.get("ParentName") or item.get("ShowName"))
        item_type = self._normalize_media_type(item.get("Type"), title, series_title)

        resolved_title = title or series_title or "Unknown title"
        resolved_series = series_title if item_type == "episode" else None
        if item_type == "show":
            resolved_series = title or series_title or "Unknown show"
            resolved_title = resolved_series

        normalized = {
            "timestamp": timestamp,
            "user_id": user_id,
            "title": resolved_title,
            "series_title": resolved_series,
            "item_type": item_type,
            "duration_seconds": duration_seconds,
            "play_count": play_count,
            "source": "api",
        }

        return [normalized]

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

    def _normalize_media_type(self, raw_type: Any, title: str | None, series_title: str | None) -> str:
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

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _coerce_int(self, value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

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


client = JellyfinClient()