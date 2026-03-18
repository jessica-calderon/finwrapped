import logging
from datetime import UTC, datetime
from typing import Any

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


class JellyfinClientError(RuntimeError):
    """Raised when Jellyfin returns an unexpected error."""


class JellyfinClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or settings.JELLYFIN_URL).rstrip("/")
        self.timeout = 15
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-Emby-Token": api_key if api_key is not None else settings.API_KEY,
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

    def get_playback_events(
        self,
        year: int | None = None,
        user_id: str | None = None,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        """
        Return normalized playback records from the Jellyfin API.

        This is a best-effort fallback when richer sources are unavailable.
        """

        users = [{"Id": user_id}] if user_id else self.get_users()
        events: list[dict[str, Any]] = []

        for user in users:
            current_user_id = user.get("Id") or user_id
            if not current_user_id:
                continue

            events.extend(self._fetch_user_items(current_user_id, year, page_size))
            if not events:
                events.extend(self._fetch_sessions(current_user_id, year))

        events.sort(key=lambda event: event["played_at"])
        return events

    def get_playback_activity(
        self,
        year: int | None = None,
        user_id: str | None = None,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        """Backward-compatible wrapper for the historical method name."""

        return self.get_playback_events(year, user_id, page_size)

    def _fetch_user_items(self, user_id: str, year: int | None, page_size: int) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        start_index = 0

        while True:
            try:
                payload = self._request_json(
                    f"/Users/{user_id}/Items",
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
                logger.warning("Unable to fetch playback items for user %s: %s", user_id, exc)
                break

            items = payload if isinstance(payload, list) else payload.get("Items", [])
            if not items:
                break

            for item in items:
                events.extend(self._normalize_item(item, year, user_id))

            if len(items) < page_size:
                break
            start_index += page_size

        return events

    def _fetch_sessions(self, user_id: str, year: int | None) -> list[dict[str, Any]]:
        try:
            payload = self._request_json("/Sessions")
        except JellyfinClientError as exc:
            logger.warning("Unable to fetch Jellyfin sessions for user %s: %s", user_id, exc)
            return []

        sessions = payload if isinstance(payload, list) else payload.get("Items", [])
        events: list[dict[str, Any]] = []

        for session in sessions:
            if not isinstance(session, dict):
                continue
            session_user_id = self._clean_text(session.get("UserId") or session.get("userId") or session.get("UserID"))
            if session_user_id and session_user_id != user_id:
                continue

            now_playing = session.get("NowPlayingItem")
            if not isinstance(now_playing, dict):
                continue

            played_at = self._parse_timestamp(
                session.get("LastPlaybackCheckIn")
                or session.get("lastPlaybackCheckIn")
                or session.get("LastActivityDate")
                or session.get("lastActivityDate")
            ) or datetime.now(tz=UTC)
            if year is not None and played_at.year != year:
                continue

            title = self._clean_text(now_playing.get("Name") or now_playing.get("Title") or now_playing.get("SeriesName"))
            if not title:
                title = "Unknown title"

            events.append(
                {
                    "user_id": session_user_id or user_id,
                    "item_name": title,
                    "item_type": self._normalize_media_type(now_playing.get("Type"), title),
                    "played_at": played_at,
                    "duration": int(round(self._coerce_duration_seconds(now_playing.get("RunTimeTicks") or now_playing.get("RuntimeTicks") or now_playing.get("Runtime")))),
                }
            )

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

    def _normalize_item(self, item: dict[str, Any], year: int | None, user_id: str) -> list[dict[str, Any]]:
        user_data = item.get("UserData") or {}
        played_at = self._parse_timestamp(
            user_data.get("LastPlayedDate")
            or user_data.get("PlayedDate")
            or item.get("LastPlayedDate")
            or item.get("DatePlayed")
            or item.get("PremiereDate")
        )
        if not played_at or (year is not None and played_at.year != year):
            return []

        play_count = max(1, self._coerce_int(user_data.get("PlayCount") or item.get("PlayCount") or 1))
        duration_seconds = int(round(self._coerce_duration_seconds(item.get("RunTimeTicks") or item.get("RuntimeTicks") or item.get("Runtime"))))

        title = self._clean_text(item.get("Name") or item.get("Title") or item.get("SeriesName") or item.get("ParentName"))
        series_title = self._clean_text(item.get("SeriesName") or item.get("ParentName") or item.get("ShowName"))
        item_type = self._normalize_media_type(item.get("Type"), title or series_title)

        item_name = title or series_title or "Unknown title"
        return [
            {
                "user_id": user_id,
                "item_name": item_name,
                "item_type": item_type,
                "played_at": played_at,
                "duration": duration_seconds,
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

    def _normalize_media_type(self, raw_type: Any, title: str | None) -> str:
        normalized = str(raw_type or "").strip().lower()
        if normalized in {"movie", "feature", "video"}:
            return "movie"
        if normalized in {"episode", "episodeitem", "series", "show"}:
            return "episode"
        return "movie" if title else "episode"

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


def create_client(base_url: str | None = None, api_key: str | None = None) -> JellyfinClient:
    return JellyfinClient(base_url=base_url, api_key=api_key)


client = JellyfinClient()