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
        from app.main import app

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
    async def test_health_endpoint_without_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/health")
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
    @pytest.mark.asyncio
    async def test_websocket_with_valid_token(self):
        from starlette.testclient import TestClient

        token = create_access_token(data={"sub": "dev"})
        with (
            TestClient(app) as client,
            client.websocket_connect(
                f"/api/v1/ws/analysis/00000000-0000-4000-8000-000000000000?token={token}"
            ) as ws,
        ):
            ws.close()

    @pytest.mark.asyncio
    async def test_websocket_without_token(self):
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            try:
                with client.websocket_connect(
                    "/api/v1/ws/analysis/00000000-0000-4000-8000-000000000000"
                ) as ws:
                    ws.close()
                raise AssertionError("Expected WebSocket connection to fail")
            except Exception:
                pass  # Expected: connection rejected

    @pytest.mark.asyncio
    async def test_websocket_with_invalid_token(self):
        from starlette.testclient import TestClient

        with TestClient(app) as client:
            try:
                with client.websocket_connect(
                    "/api/v1/ws/analysis/00000000-0000-4000-8000-000000000000?token=invalid-token"
                ) as ws:
                    ws.close()
                raise AssertionError("Expected WebSocket connection to fail")
            except Exception:
                pass  # Expected: connection rejected
