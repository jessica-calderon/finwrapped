from datetime import datetime

def get_basic_stats(year: int, user_id: str = None):
    return {
        "year": year,
        "user": user_id,
        "total_hours": 0,
        "top_movies": [],
        "top_shows": [],
        "generated_at": datetime.utcnow().isoformat()
    }