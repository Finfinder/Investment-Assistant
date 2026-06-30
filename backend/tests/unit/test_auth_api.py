"""Integration tests for auth endpoint and protected API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.core.config import get_settings
from app.main import app


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_success(self, db_session: AsyncSession):
        import unittest.mock as mock

        from httpx import ASGITransport, AsyncClient

        from app.core.auth import hash_password
        from app.core.database import get_db

        hashed = hash_password("dev-password")
        real_settings = get_settings()

        async def _override_get_db():
            yield db_session

        def _mock_get_settings():
            import contextlib

            s = mock.MagicMock()
            # Copy all real settings, override only auth fields
            for attr in dir(real_settings):
                if not attr.startswith("_"):
                    with contextlib.suppress(AttributeError):
                        setattr(s, attr, getattr(real_settings, attr))
            s.AUTH_USERNAME = "dev"
            s.AUTH_PASSWORD_HASH = hashed
            return s

        with mock.patch("app.core.auth.get_settings", side_effect=_mock_get_settings):
            app.dependency_overrides[get_db] = _override_get_db
            try:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    response = await ac.post(
                        "/api/v1/auth/token",
                        data={"username": "dev", "password": "dev-password"},
                    )
                    assert response.status_code == 200
                    data = response.json()
                    assert "access_token" in data
                    assert data["token_type"] == "bearer"  # noqa: S105
            finally:
                app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "dev", "password": "wrong"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/token",
            data={"username": "unknown", "password": "dev"},
        )
        assert response.status_code == 401


class TestProtectedEndpoints:
    @pytest.mark.asyncio
    async def test_health_endpoint_without_auth(self, raw_client: AsyncClient):
        """Health endpoint remains accessible without authentication (monitoring)."""
        response = await raw_client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_market_data_with_valid_token(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/market-data/AAPL")
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_market_data_without_token(self, raw_client: AsyncClient):
        response = await raw_client.get("/api/v1/market-data/AAPL")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_market_data_with_invalid_token(self, raw_client: AsyncClient):
        headers = {"Authorization": "Bearer invalid-token"}
        response = await raw_client.get("/api/v1/market-data/AAPL", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_market_data_with_expired_token(self, raw_client: AsyncClient):
        from datetime import timedelta

        token = create_access_token(data={"sub": "dev"}, expires_delta=timedelta(minutes=-1))
        headers = {"Authorization": f"Bearer {token}"}
        response = await raw_client.get("/api/v1/market-data/AAPL", headers=headers)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_analysis_endpoint_with_valid_token(self, auth_client: AsyncClient):
        response = await auth_client.get("/api/v1/analysis/invalid-uuid")
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_analysis_endpoint_without_token(self, raw_client: AsyncClient):
        response = await raw_client.get("/api/v1/analysis/invalid-uuid")
        assert response.status_code == 401


class TestWebSocketAuth:
    """WebSocket auth tested via ws_require_auth unit tests.
    TestClient-based integration tests are omitted because they trigger the
    app lifespan (requiring REDIS_PASSWORD) which is unavailable in unit test CI jobs.
    The underlying ws_require_auth function is fully covered in test_auth.py.
    """

    def test_ws_require_auth_rejects_empty_token(self):
        from fastapi import WebSocketException

        from app.core.auth import ws_require_auth

        with pytest.raises(WebSocketException) as exc_info:
            ws_require_auth("")
        assert exc_info.value.code == 1008

    def test_ws_require_auth_rejects_invalid_token(self):
        from fastapi import WebSocketException

        from app.core.auth import ws_require_auth

        with pytest.raises(WebSocketException) as exc_info:
            ws_require_auth("not-a-jwt")
        assert exc_info.value.code == 1008

    def test_ws_require_auth_accepts_valid_token(self):
        from app.core.auth import ws_require_auth

        token = create_access_token(data={"sub": "dev"})
        result = ws_require_auth(token)
        assert result == "dev"
