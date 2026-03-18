# FinWrapped

FinWrapped is a small FastAPI + React app for generating Jellyfin viewing recaps.

## What it does

- Shows a recap experience for a selected year
- Pulls user and playback data from Jellyfin or Jellystat
- Offers an onboarding flow and settings panel for saving server config locally in the browser
- Exposes a simple API for recap stats, user lookup, and connection testing
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
- Optional Jellystat instance if you want to use Jellystat as a data source

The first launch opens a local onboarding flow where you can save Jellyfin and optional Jellystat settings directly in the browser. The backend still uses environment variables as a fallback, but runtime requests can override them from the saved config without restarting the server.

### Environment

Create a `.env` file in the project root:

```env
JELLYFIN_URL=http://localhost:8096
API_KEY=your_jellyfin_api_key
DATA_MODE=auto
PLAYBACK_DB_PATH=/config/data/playback_reporting.db
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8091,http://127.0.0.1:8091
```

Environment variables act as defaults for the backend:

- `JELLYFIN_URL` and `API_KEY` are used when no saved browser config is available.
- `DATA_MODE` controls which data source is used at request time. Supported values are `auto`, `jellystat`, `jellyfin`, and `sync`.
- `PLAYBACK_DB_PATH` points to the Jellyfin playback database when you want local DB reads.
- `CORS_ORIGINS` should include any frontend hostnames you use during development.

If you want FinWrapped and Jellyfin to talk over the same Docker network during local dev, FinWrapped joins the `server-stack_homelab` network used by your `@server-stack` setup. That lets the app reach Jellyfin by container name.

In that setup, the Jellyfin URL inside FinWrapped is usually:

```text
http://jellyfin:8096
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
- `POST /api/test/jellyfin` - verify a Jellyfin connection from onboarding
- `POST /api/test/jellystat` - verify a Jellystat connection from onboarding
- `GET /recap/{year}/view` - HTML recap page

## Support

If you like this project, consider buying me a coffee:

[Buy me a coffee](https://www.buymeacoffee.com/)
