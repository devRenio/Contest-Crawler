from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = "sqlite:///./data/contests.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_model_review: str = "gemini-3.8-flash"
    database_url: str = DEFAULT_DATABASE_URL
    cors_origins: str = "http://localhost:3000"
    user_agent: str = (
        "ContestCrawler/0.1 (club-internal; +https://github.com/devRenio/Contest-Crawler)"
    )
    request_delay_sec: float = 1.2
    lite_daily_cap: int = 80
    review_daily_cap: int = 10
    new_days: int = 7
    closing_days: int = 14
    max_pages: int = 8

    @field_validator("database_url", mode="before")
    @classmethod
    def nonempty_database_url(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return DEFAULT_DATABASE_URL
        return value


settings = Settings()
