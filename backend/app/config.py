from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY_AUTH: str
    USE_SQLITE_DB: bool = True
    SQLITE_DB_URL: str = ""
    DB_USER: str = "default_user"
    DB_PASSWORD: str = "default_password"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    SENTRY_DSN: str = ""
    STATIC_FILES_DIR: str = "./dist"
    MAILTRAP_API_KEY: str = ""
    APP_BASE_URL: str = "https://golf.bronnerapp.com"
    FROM_EMAIL: str = "noreply@bronnerapp.com"
    FROM_NAME: str = "GolfMapper"
    MAP_FILES_DIR: str = "./static/user_maps"
    TRACES_SAMPLE_RATE: float = 0.1
    TOKEN_EXPIRE_MINUTES: int = 90
    # Overridable per deployment without a code change via the CORS_ORIGINS
    # env var (JSON list), e.g. CORS_ORIGINS='["https://golf.bronnerapp.com"]'
    CORS_ORIGINS: list[str] = [
        # Local development
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "https://127.0.0.1:3000",
        "http://localhost:8005",
        "http://127.0.0.1:8005",
        "https://localhost:8005",
        "https://localhost",
        "https://127.0.0.1",
        "https://127.0.0.1:8005",
        "http://localhost:23441",
        # LAN / cloud dev hosts
        "https://10.9.8.221:3000",
        "http://10.9.8.221:3000",
        "https://132.145.156.224:3000",
        "http://132.145.156.224:3000",
        # Deployed environments
        "https://golf.bronnerapp.com",
        "http://golf.bronnerapp.com",
        "https://backend.bronnerapp.com",
        "http://backend.bronnerapp.com",
        "https://golf-stage.lab.bronnerapp.com",
        "http://golf-stage.lab.bronnerapp.com",
    ]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
