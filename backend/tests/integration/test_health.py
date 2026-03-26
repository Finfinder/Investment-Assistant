"""Tests for health check endpoint."""

from httpx import AsyncClient


class TestHealthCheck:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
