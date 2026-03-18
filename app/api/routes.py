from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl

from app.main import templates
from app.services.analytics import get_basic_stats
from app.services.jellyfin_client import JellyfinClient, create_client
from app.services.users import get_user, list_users

router = APIRouter()


class JellyfinTestRequest(BaseModel):
    url: HttpUrl
    apiKey: str


class JellystatTestRequest(BaseModel):
    url: HttpUrl


def _clean_header(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    return cleaned or None


def _normalize_data_mode(value: str | None) -> str:
    cleaned = _clean_header(value)
    normalized = cleaned.lower() if cleaned else ""
    return normalized if normalized in {"auto", "jellystat", "jellyfin", "sync"} else "auto"


def _resolve_jellyfin_client(request: Request | None = None) -> JellyfinClient:
    if request is None:
        return create_client()

    jellyfin_url = _clean_header(request.headers.get("X-Jellyfin-Url"))
    jellyfin_key = _clean_header(request.headers.get("X-Jellyfin-Key"))

    if jellyfin_url or jellyfin_key:
        return create_client(jellyfin_url, jellyfin_key)

    return create_client()


def _resolve_request_config(request: Request | None = None) -> dict[str, dict[str, Any]]:
    if request is None:
        return {
            "jellyfin": {"url": "", "apiKey": ""},
            "jellystat": {"url": "", "enabled": False},
            "dataMode": "auto",
        }

    jellyfin_url = _clean_header(request.headers.get("X-Jellyfin-Url")) or ""
    jellyfin_key = _clean_header(request.headers.get("X-Jellyfin-Key")) or ""
    jellystat_url = _clean_header(request.headers.get("X-Jellystat-Url")) or ""

    return {
        "jellyfin": {
            "url": jellyfin_url,
            "apiKey": jellyfin_key,
        },
        "jellystat": {
            "url": jellystat_url,
            "enabled": bool(jellystat_url),
        },
        "dataMode": _normalize_data_mode(request.headers.get("X-Data-Mode")),
    }


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/users")
def users(request: Request) -> list[dict[str, str]]:
    """Return a minimal list of Jellyfin users for selection in the UI."""

    return list_users(_resolve_jellyfin_client(request))


@router.get("/api/recap")
def recap_range(request: Request, range: str = "30d") -> dict[str, object]:
    """Return global recap stats for a selected time range."""

    return get_basic_stats(
        None,
        config=_resolve_request_config(request),
        jellyfin_client=_resolve_jellyfin_client(request),
        range_key=range,
    )


@router.get("/api/recap/{year}")
def recap(year: int, request: Request, range: str | None = None) -> dict[str, object]:
    """Return global recap stats for a given year or time range."""

    return get_basic_stats(
        year,
        config=_resolve_request_config(request),
        jellyfin_client=_resolve_jellyfin_client(request),
        range_key=range,
    )


@router.get("/recap/{year}/view", response_class=HTMLResponse)
def recap_view(request: Request, year: int) -> HTMLResponse:
    return templates.TemplateResponse(
        "recap.html",
        {
            "request": request,
            "year": year,
        },
    )


@router.get("/api/recap/user/{user_id}")
def recap_user_range(request: Request, user_id: str, range: str = "30d") -> dict[str, object]:
    """Return recap stats filtered to a single Jellyfin user."""

    jellyfin_client = _resolve_jellyfin_client(request)

    if get_user(user_id, jellyfin_client) is None:
        raise HTTPException(status_code=404, detail="User not found")

    return get_basic_stats(
        None,
        user_id,
        _resolve_request_config(request),
        jellyfin_client,
        range_key=range,
    )


@router.get("/api/recap/{year}/user/{user_id}")
def recap_user(year: int, user_id: str, request: Request, range: str | None = None) -> dict[str, object]:
    """Return recap stats filtered to a single Jellyfin user."""

    jellyfin_client = _resolve_jellyfin_client(request)

    if get_user(user_id, jellyfin_client) is None:
        raise HTTPException(status_code=404, detail="User not found")

    return get_basic_stats(year, user_id, _resolve_request_config(request), jellyfin_client, range_key=range)


@router.post("/api/test/jellyfin")
def test_jellyfin_connection(payload: JellyfinTestRequest) -> dict[str, Any]:
    client = create_client(str(payload.url), payload.apiKey)

    try:
        client._request_json("/System/Info")
    except Exception as exc:  # noqa: BLE001 - surfaced to the onboarding UI
        raise HTTPException(status_code=400, detail=f"Unable to reach Jellyfin: {exc}") from exc

    return {"ok": True}


@router.post("/api/test/jellystat")
def test_jellystat_connection(payload: JellystatTestRequest) -> dict[str, Any]:
    base_url = str(payload.url).rstrip("/")
    health_paths = ("/api/health", "/health", "/api/status")

    last_error: str | None = None
    for path in health_paths:
        try:
            response = requests.get(f"{base_url}{path}", timeout=10)
            if response.ok:
                return {"ok": True, "endpoint": path}
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            last_error = str(exc)

    raise HTTPException(
        status_code=400,
        detail=f"Unable to reach Jellystat: {last_error or 'unknown error'}",
    )