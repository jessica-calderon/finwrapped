import requests
from app.core.config import settings

class JellyfinClient:
    def __init__(self):
        self.base_url = settings.JELLYFIN_URL
        self.headers = {
            "X-Emby-Token": settings.API_KEY
        }

    def get_users(self):
        url = f"{self.base_url}/Users"
        r = requests.get(url, headers=self.headers)
        return r.json()

    def get_items(self):
        url = f"{self.base_url}/Items"
        r = requests.get(url, headers=self.headers)
        return r.json()

client = JellyfinClient()