from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.main import templates
from app.services.analytics import get_basic_stats

router = APIRouter()

@router.get("/api/health")
def health():
    return {"status": "ok"}

@router.get("/api/recap/{year}")
def recap(year: int):
    return get_basic_stats(year)


@router.get("/recap/{year}/view", response_class=HTMLResponse)
def recap_view(request: Request, year: int):
    return templates.TemplateResponse(
        "recap.html",
        {
            "request": request,
            "year": year,
        },
    )

@router.get("/api/recap/{year}/user/{user_id}")
def recap_user(year: int, user_id: str):
    return get_basic_stats(year, user_id)