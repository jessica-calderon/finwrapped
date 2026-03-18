from __future__ import annotations

from typing import Any

from app.services.jellyfin_client import client


def list_users() -> list[dict[str, str]]:
    """Return a sanitized list of Jellyfin users."""

    users: list[dict[str, str]] = []
    for raw_user in client.get_users():
        user = _normalize_user(raw_user)
        if user is not None:
            users.append(user)
    return users


def get_user(user_id: str) -> dict[str, str] | None:
    """Return a sanitized Jellyfin user by id, if it exists."""

    for user in list_users():
        if user["id"] == user_id:
            return user
    return None


def _normalize_user(raw_user: Any) -> dict[str, str] | None:
    if not isinstance(raw_user, dict):
        return None

    user_id = _clean_text(raw_user.get("Id") or raw_user.get("id"))
    if not user_id:
        return None

    name = _clean_text(
        raw_user.get("Name")
        or raw_user.get("Username")
        or raw_user.get("DisplayName")
        or raw_user.get("name")
    ) or user_id

    return {"id": user_id, "name": name}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
