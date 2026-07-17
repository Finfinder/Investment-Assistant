"""Tests verifying the middleware registration order in create_app().

CORSMiddleware must be the outermost (last-registered) middleware so it acts as
the entry/exit boundary for every request, including preflight OPTIONS handling.
This resolves SonarCloud rule python:S8414. See issue #238 (IA-172).
"""

import pytest
from fastapi.middleware.cors import CORSMiddleware

from app.core.security_headers import SecurityHeadersMiddleware
from tests.helpers import make_app


@pytest.fixture
def prod_app():
    """App with DEBUG=False so security headers middleware is registered."""
    with make_app(debug=False) as app:
        yield app


@pytest.fixture
def dev_app():
    """App with DEBUG=True so security headers middleware is skipped."""
    with make_app(debug=True) as app:
        yield app


class TestMiddlewareOrderProduction:
    def test_cors_is_outermost_middleware(self, prod_app) -> None:
        assert prod_app.user_middleware[0].cls is CORSMiddleware

    def test_security_headers_registered_inside_cors(self, prod_app) -> None:
        middleware_classes = [mw.cls for mw in prod_app.user_middleware]
        assert SecurityHeadersMiddleware in middleware_classes
        assert middleware_classes.index(SecurityHeadersMiddleware) > middleware_classes.index(CORSMiddleware)


class TestMiddlewareOrderDevelopment:
    def test_cors_is_outermost_middleware(self, dev_app) -> None:
        assert dev_app.user_middleware[0].cls is CORSMiddleware

    def test_security_headers_not_registered_in_development(self, dev_app) -> None:
        middleware_classes = [mw.cls for mw in dev_app.user_middleware]
        assert SecurityHeadersMiddleware not in middleware_classes
