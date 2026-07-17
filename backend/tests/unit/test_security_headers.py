"""Tests for security response headers middleware."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security_headers import SECURITY_HEADERS, SecurityHeadersMiddleware
from tests.helpers import make_app


def _make_client(debug: bool) -> AsyncClient:
    """Create a fresh app with DEBUG overridden and return an AsyncClient."""
    test_app = make_app(debug=debug)
    transport = ASGITransport(app=test_app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def prod_client() -> AsyncGenerator[AsyncClient]:
    """AsyncClient with DEBUG=False so security headers are active."""
    async with _make_client(debug=False) as client:
        yield client


@pytest.fixture
async def dev_client() -> AsyncGenerator[AsyncClient]:
    """AsyncClient with DEBUG=True so security headers are skipped."""
    async with _make_client(debug=True) as client:
        yield client


class TestSecurityHeadersProduction:
    async def test_security_headers_present_on_health(self, prod_client: AsyncClient) -> None:
        response = await prod_client.get("/api/v1/health")
        assert response.status_code == 200
        for header, value in SECURITY_HEADERS.items():
            assert response.headers.get(header) == value

    async def test_security_headers_present_on_error_response(self, prod_client: AsyncClient) -> None:
        # Unauthenticated access to a protected endpoint returns 401/403
        response = await prod_client.get("/api/v1/health/dependencies")
        assert response.status_code in (401, 403)
        for header, value in SECURITY_HEADERS.items():
            assert response.headers.get(header) == value

    async def test_hsts_header_value(self, prod_client: AsyncClient) -> None:
        response = await prod_client.get("/api/v1/health")
        assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"

    async def test_csp_is_minimal_for_api(self, prod_client: AsyncClient) -> None:
        response = await prod_client.get("/api/v1/health")
        assert response.headers.get("Content-Security-Policy") == "default-src 'none'"


class TestSecurityHeadersDevelopment:
    async def test_security_headers_absent_in_development(self, dev_client: AsyncClient) -> None:
        response = await dev_client.get("/api/v1/health")
        assert response.status_code == 200
        for header in SECURITY_HEADERS:
            assert response.headers.get(header) is None


class TestSecurityHeadersMiddlewareUnit:
    def test_middleware_adds_headers_without_overwriting(self) -> None:
        from starlette.requests import Request
        from starlette.responses import Response

        async def call_next(_: object) -> Response:
            return Response(content="ok", headers={"X-Frame-Options": "SAMEORIGIN"})

        middleware = SecurityHeadersMiddleware(app=None)  # type: ignore[arg-type]

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        request = Request(scope)

        async def run() -> Response:
            return await middleware.dispatch(request, call_next)

        import asyncio

        result = asyncio.run(run())
        # Existing header is preserved (setdefault semantics)
        assert result.headers.get("X-Frame-Options") == "SAMEORIGIN"
        # Other security headers are added
        assert result.headers.get("X-Content-Type-Options") == "nosniff"
        assert result.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
