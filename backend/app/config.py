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
    MAP_FILES_DIR: str = "./static/user_maps"
    TRACES_SAMPLE_RATE: float = 0.1
    TOKEN_EXPIRE_MINUTES: int = 90

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
