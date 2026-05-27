from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    marketdata_token: str = Field("", alias="MARKETDATA_TOKEN")
    anthropic_api_key: str = Field(..., alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-haiku-4-5-20251001", alias="ANTHROPIC_MODEL")

    database_url: str = Field(
        "sqlite+aiosqlite:///./data/signals.db", alias="DATABASE_URL"
    )
    watchlist_path: Path = Field(Path("./config/watchlist.yaml"), alias="WATCHLIST_PATH")

    log_level: str = Field("INFO", alias="LOG_LEVEL")
    scheduler_interval_seconds: int = Field(60, alias="SCHEDULER_INTERVAL_SECONDS")
    scheduler_max_concurrency: int = Field(5, alias="SCHEDULER_MAX_CONCURRENCY")

    marketdata_base_url: str = "https://api.marketdata.app/v1"
    marketdata_rate_limit_per_minute: int = 8


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
