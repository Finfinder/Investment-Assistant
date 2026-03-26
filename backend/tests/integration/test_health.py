"""Tests for health check endpoints."""

from httpx import AsyncClient


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    async def test_health_dependencies(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "yfinance" in data
        assert data["yfinance"] == "ok"
