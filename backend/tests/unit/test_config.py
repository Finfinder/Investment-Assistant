"""Tests for configuration loading."""

from unittest.mock import patch

from app.core.config import Settings


def test_settings_default_values() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert settings.APP_NAME == "Investment Assistant"
    assert settings.DEBUG is False
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.CACHE_TTL_INTRADAY == 300
    assert settings.CACHE_TTL_DAILY == 3600


def test_settings_loads_from_env() -> None:
    env_vars = {
        "APP_NAME": "Test App",
        "DEBUG": "true",
        "DATABASE_URL": "sqlite+aiosqlite:///test.db",
        "TWELVE_DATA_API_KEY": "test-key-12",
        "FMP_API_KEY": "test-key-fmp",
        "FRED_API_KEY": "test-key-fred",
    }
    with patch.dict("os.environ", env_vars, clear=False):
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.APP_NAME == "Test App"
        assert settings.DEBUG is True
        assert settings.DATABASE_URL == "sqlite+aiosqlite:///test.db"
        assert settings.TWELVE_DATA_API_KEY == "test-key-12"
        assert settings.FMP_API_KEY == "test-key-fmp"
        assert settings.FRED_API_KEY == "test-key-fred"


def test_settings_cors_origins_default() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.CORS_ORIGINS == ["http://localhost:3000"]
