# GolfMapper2 API

A FastAPI API to manage golf courses played by a user. Designed to use gm2-react as a frontend.

## Database Support

Currently supports SQLite (default) or PostgreSQL as the database.

## Required Environmental Variables

- `SECRET_KEY_AUTH`: Set to a random string to encode the JWT tokens.

## Optional Environmental Variables

- `DB_USER`: PostgreSQL user (default: `default_user`)
- `DB_PASSWORD`: PostgreSQL password (default: `default_password`)
- `DB_HOST`: PostgreSQL host (default: `localhost`)
- `DB_PORT`: PostgreSQL port (default: `5432`)
- `USE_SQLITE_DB`: Use SQLite over PostgreSQL (default: `true`)
- `SQLITE_DB_URL`: SQLite database URL (default: `None`)
- `SENTRY_DSN`: Sentry DSN (default: `""`)