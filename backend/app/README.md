# GolfMapper3 API

A FastAPI backend to track golf courses played by each user and render them on
folium maps. Serves the built React frontend (from `STATIC_FILES_DIR`) in
production, so the app runs as a single container.

## Database Support

SQLite (default) or PostgreSQL.

## Required Environment Variables

- `SECRET_KEY_AUTH`: Random string used to sign JWT tokens (HS256 — use 32+ bytes).

## Optional Environment Variables

- `USE_SQLITE_DB`: Use SQLite instead of PostgreSQL (default: `true`)
- `SQLITE_DB_URL`: Path to the SQLite file (default: `app/golf_mapper.db`)
- `DB_USER`: PostgreSQL user (default: `default_user`)
- `DB_PASSWORD`: PostgreSQL password (default: `default_password`)
- `DB_HOST`: PostgreSQL host (default: `localhost`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `STATIC_FILES_DIR`: Built frontend to serve (default: `./dist`)
- `MAP_FILES_DIR`: Where generated user map HTML is cached (default: `./static/user_maps`)
- `TOKEN_EXPIRE_MINUTES`: JWT lifetime (default: `90`)
- `CORS_ORIGINS`: JSON list of allowed origins, overrides the built-in list
  (e.g. `CORS_ORIGINS='["https://golf.bronnerapp.com"]'`)
- `MAILTRAP_API_KEY`: Enables password-reset emails (skipped if unset)
- `APP_BASE_URL`: Base URL used in password-reset links (default: `https://golf.bronnerapp.com`)
- `FROM_EMAIL` / `FROM_NAME`: Password-reset email sender (defaults: `noreply@bronnerapp.com` / `GolfMapper`)
- `SENTRY_DSN`: Sentry DSN (default: disabled)
- `TRACES_SAMPLE_RATE`: Sentry traces sample rate (default: `0.1`)

Variables can also be set in `app/.env`.

## Development

```bash
cd backend
uv sync          # installs runtime + dev dependencies (pytest, ruff)
uv run pytest    # run the test suite (in-memory SQLite, no env setup needed)
uv run ruff check .
uv run uvicorn app.main:app --reload --port 8005
```

One-off maintenance tools live in `backend/scripts/` (not part of the app package).
