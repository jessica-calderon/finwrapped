# FinWrapped

FinWrapped is a small FastAPI + React app for generating Jellyfin viewing recaps.

## What it does

- Shows a recap experience for a selected year
- Pulls user and playback data from Jellyfin
- Exposes a simple API for recap stats and user lookup
- Serves a web UI and a recap view page

## Tech Stack

- Backend: Python, FastAPI, Jinja2
- Frontend: React, Vite
- Deployment: Docker / Docker Compose

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+ for the frontend
- A Jellyfin instance with an API key

### Environment

Create a `.env` file in the project root:

```env
JELLYFIN_URL=http://localhost:8096
API_KEY=your_jellyfin_api_key
DATA_MODE=api
PLAYBACK_DB_PATH=/config/data/playback_reporting.db
```

### Run with Docker

```bash
docker compose up --build
```

The app will be available on `http://localhost:8091`.

### Run locally

Backend:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Key Routes

- `GET /` - health response
- `GET /api/health` - API health check
- `GET /api/users` - list Jellyfin users
- `GET /api/recap/{year}` - recap stats for a year
- `GET /api/recap/{year}/user/{user_id}` - recap stats for one user
- `GET /recap/{year}/view` - HTML recap page

## Support

If you like this project, consider buying me a coffee:

[Buy me a coffee](https://www.buymeacoffee.com/)
