from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.main import templates
from app.services.analytics import get_basic_stats
from app.services.users import get_user, list_users

router = APIRouter()


@router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/users")
def users() -> list[dict[str, str]]:
    """Return a minimal list of Jellyfin users for selection in the UI."""

    return list_users()


@router.get("/api/recap/{year}")
def recap(year: int) -> dict[str, object]:
    """Return global recap stats for a given year."""

    return get_basic_stats(year)


@router.get("/recap/{year}/view", response_class=HTMLResponse)
def recap_view(request: Request, year: int) -> HTMLResponse:
    return templates.TemplateResponse(
        "recap.html",
        {
            "request": request,
            "year": year,
        },
    )


@router.get("/api/recap/{year}/user/{user_id}")
def recap_user(year: int, user_id: str) -> dict[str, object]:
    """Return recap stats filtered to a single Jellyfin user."""

    if get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    return get_basic_stats(year, user_id)