import ipaddress
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @field_validator("ALGORITHM")
    @classmethod
    def algorithm_must_be_supported(cls, v: str) -> str:
        supported = {"HS256", "HS384", "HS512"}
        if v not in supported:
            raise ValueError(f"Unsupported JWT algorithm: {v}. Must be one of {sorted(supported)}")
        return v

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

    # Authentication
    SECRET_KEY: str = "dev-secret-key-change-in-production"  # noqa: S105
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AUTH_USERNAME: str = "dev"
    AUTH_PASSWORD_HASH: str = ""

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]

    # Trusted proxy CIDRs for X-Forwarded-For validation (rate limiting anti-spoofing)
    TRUSTED_PROXIES: list[str] = []

    # WebSocket per-IP connection limiter
    WS_MAX_CONNECTIONS_PER_IP: int = 5
    WS_CONNECTION_TTL_SECONDS: int = 300
    # WebSocket max connection duration and keep-alive heartbeat (Issue #119)
    WS_MAX_CONNECTION_DURATION_SECONDS: int = 60
    WS_PING_INTERVAL_SECONDS: int = 30

    @field_validator("TRUSTED_PROXIES")
    @classmethod
    def trusted_proxies_must_be_valid_cidr(cls, v: list[str]) -> list[str]:
        for entry in v:
            try:
                ipaddress.ip_network(entry, strict=False)
            except ValueError as err:
                raise ValueError(f"Invalid TRUSTED_PROXIES entry '{entry}': {err}") from err
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
