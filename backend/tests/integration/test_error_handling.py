"""Integration tests for centralized error handling and correlation IDs."""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


def _make_client(debug: bool) -> AsyncClient:
    """Create a fresh app with DEBUG overridden and auth bypassed."""
    import contextlib

    get_settings.cache_clear()
    real = get_settings()
    settings = MagicMock()
    # Mirror real settings, then override DEBUG.
    for attr in dir(real):
        if not attr.startswith("_"):
            with contextlib.suppress(Exception):
                setattr(settings, attr, getattr(real, attr))
    settings.DEBUG = debug
    with patch("app.main.get_settings", return_value=settings):
        from app.core.auth import require_auth
        from app.main import create_app

        test_app = create_app()
        # Bypass authentication so error-handling paths are exercised directly.
        test_app.dependency_overrides[require_auth] = lambda: "dev"
    transport = ASGITransport(app=test_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def prod_client() -> AsyncGenerator[AsyncClient]:
    """Client with DEBUG=False so generic error messages are returned."""
    client = _make_client(debug=False)
    async with client:
        yield client


@pytest.fixture
async def dev_client() -> AsyncGenerator[AsyncClient]:
    """Client with DEBUG=True so descriptive (but safe) messages are returned."""
    client = _make_client(debug=True)
    async with client:
        yield client


class TestErrorHandlingProduction:
    async def test_500_returns_sanitized_shape_with_reference(self, prod_client: AsyncClient) -> None:
        with patch(
            "app.modules.fundamental_analysis.forex.analyze_forex",
            side_effect=RuntimeError("internal /secret/path detail"),
        ):
            resp = await prod_client.post(
                "/api/v1/fundamental-analysis",
                json={"symbol": "EURUSD"},
            )
        assert resp.status_code == 500
        data = resp.json()
        assert set(data.keys()) == {"error", "reference"}
        assert data["reference"]
        # No internal details leak to the client.
        assert "/" not in data["error"]
        assert "secret" not in data["error"]
        # The correlation ID must be echoed back so the client can correlate
        # the error with server logs even on the unhandled-exception path.
        assert resp.headers["X-Request-ID"] == data["reference"]

    async def test_422_validation_error_uses_sanitized_shape(self, prod_client: AsyncClient) -> None:
        # Missing required field "symbol" triggers RequestValidationError.
        resp = await prod_client.post("/api/v1/fundamental-analysis", json={})
        assert resp.status_code == 422
        data = resp.json()
        assert set(data.keys()) == {"error", "reference"}
        assert data["reference"]


class TestErrorHandlingDevelopment:
    async def test_500_returns_reference_not_traceback(self, dev_client: AsyncClient) -> None:
        with patch(
            "app.modules.fundamental_analysis.forex.analyze_forex",
            side_effect=RuntimeError("internal /secret/path detail"),
        ):
            resp = await dev_client.post(
                "/api/v1/fundamental-analysis",
                json={"symbol": "EURUSD"},
            )
        assert resp.status_code == 500
        data = resp.json()
        assert set(data.keys()) == {"error", "reference"}
        assert data["reference"]
        # Even in DEBUG, stack traces, internal paths and exception type
        # names must not leak to the client.
        assert "Traceback" not in data["error"]
        assert "/" not in data["error"]
        assert "RuntimeError" not in data["error"]
