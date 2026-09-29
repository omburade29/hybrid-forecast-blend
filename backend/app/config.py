"""Runtime configuration.

Values come from environment variables or a `.env` file in the backend directory.
SQLite is the default so the demo runs without PostgreSQL. Point DATABASE_URL at
Postgres in production (see README).
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/hybrid.db"
    jwt_secret: str = "development-only-please-change-me!!"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    refresh_token_days: int = 7
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    demo_email: str = "analyst@example.com"
    demo_password: str = "Forecast#2026"
    demo_name: str = "Duty Analyst"
    disable_scheduler: bool = False
    schedule_hours: int = 6

    model_config = SettingsConfigDict(env_file=str(BACKEND_ROOT / ".env"), extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        prefix = "sqlite:///./"
        if url.startswith(prefix):
            path = (BACKEND_ROOT / url[len(prefix) :]).resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            return "sqlite:///" + path.as_posix()
        return url


settings = Settings()
