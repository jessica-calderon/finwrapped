from fastapi import APIRouter
from app.services.analytics import get_basic_stats

router = APIRouter()

@router.get("/api/health")
def health():
    return {"status": "ok"}

@router.get("/api/recap/{year}")
def recap(year: int):
    return get_basic_stats(year)

@router.get("/api/recap/{year}/user/{user_id}")
def recap_user(year: int, user_id: str):
    return get_basic_stats(year, user_id)