"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Security: version and uptime removed to prevent information disclosure
        assert "version" not in data
        assert "uptime_seconds" not in data

    async def test_health_dependencies_without_auth(self, raw_client: AsyncClient) -> None:
        """Test that /health/dependencies requires authentication."""
        response = await raw_client.get("/api/v1/health/dependencies")
        assert response.status_code == 401

    async def test_health_dependencies_with_auth(self, auth_client: AsyncClient) -> None:
        """Test that /health/dependencies returns details when authenticated."""
        response = await auth_client.get("/api/v1/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "yfinance" in data
        assert data["yfinance"] == "ok"
        # Security: verify API key status is exposed only to authenticated users
        assert "twelve_data" in data
        assert "fmp" in data
        assert "fred" in data
