from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "Investment Assistant"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/investment_assistant.db"

    # Data provider API keys
    TWELVE_DATA_API_KEY: str = ""
    FMP_API_KEY: str = ""
    FRED_API_KEY: str = ""

    # Cache
    CACHE_TTL_INTRADAY: int = 300
    CACHE_TTL_DAILY: int = 3600

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_CACHE_TTL_OVERRIDE: int | None = None

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
