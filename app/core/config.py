import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://localhost:8096")
    API_KEY = os.getenv("API_KEY", "")
    DATA_MODE = os.getenv("DATA_MODE", "api")  # api | hybrid
    PLAYBACK_DB_PATH = os.getenv("PLAYBACK_DB_PATH", "")

settings = Settings()
