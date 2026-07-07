"""Security response headers middleware for the FastAPI backend.

Adds HTTP security headers to every API response in production mode to
mitigate common web attacks (downgrade, clickjacking, MIME sniffing, XSS).
"""

import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Single source of truth for security header values.
# API responses are not browser-rendered, so CSP is minimal (default-src 'none').
SECURITY_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'none'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security headers into every response when enabled.

    The middleware is registered conditionally in ``create_app()`` only when
    the application runs in production mode (``DEBUG=False``), so local
    development with hot reload is not affected by restrictive headers.
    """

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
