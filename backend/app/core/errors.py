"""Centralized error handling with correlation IDs.

Provides a middleware that assigns a correlation ID (UUID4) to every request
and propagates it to logs, plus exception handlers that return a sanitized
error response to clients while logging the full exception chain server-side.

This resolves the "exception handler masks exception chain (from None)" issue:
the full traceback is preserved in logs (with the correlation ID) and the
client only receives a generic, safe message plus a reference UUID.

Note: the correlation-ID middleware is implemented as a function-based
``@app.middleware("http")`` handler rather than ``BaseHTTPMiddleware``. The
latter does not compose correctly with Starlette's exception handlers - the
handled response is bypassed and the original exception escapes to
``ServerErrorMiddleware``. The function-based middleware runs inside the
exception-handling scope, so sanitized responses are returned as expected.
"""

import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.logging_config import correlation_id_var

logger = logging.getLogger(__name__)

# Generic, safe message returned to clients in production for unexpected errors.
_GENERIC_SERVER_ERROR = "Wewnetrzny blad serwera. Skontaktuj sie z administratorem referencyjnie."


def _get_correlation_id(request: Request) -> str:
    """Return the correlation ID stored on the request by the middleware."""
    value = getattr(request.state, "correlation_id", None)
    return str(value) if value else ""


async def correlation_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Assign a correlation ID to every request and propagate it to logs.

    The ID is stored both on ``request.state`` (so exception handlers can read
    it) and in a context variable (so the JSON formatter can attach it to every
    log record emitted while serving the request). It is also echoed back to the
    client via the ``X-Request-ID`` response header for easy tracing.

    Any exception escaping the downstream app is caught here so the full chain
    is logged (with the correlation ID) and a sanitized 500 response is returned
    to the client. Catching here guarantees the behavior regardless of
    ``ExceptionMiddleware`` handler ordering.
    """
    correlation_id = uuid.uuid4().hex
    request.state.correlation_id = correlation_id
    token = correlation_id_var.set(correlation_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        return response
    except Exception as exc:  # catch-all to sanitize response
        return await _unhandled_exception_handler(request, exc)
    finally:
        correlation_id_var.reset(token)


def build_error_response(message: str, reference: str, status_code: int) -> JSONResponse:
    """Build a sanitized JSON error response.

    The response never contains stack traces, internal paths or exception
    details - only a human-readable message and a correlation reference.
    """
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "reference": reference},
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected server errors.

    Logs the full exception chain (with correlation ID) and returns a safe,
    generic response to the client.
    """
    reference = _get_correlation_id(request)
    logger.exception(
        "Nieobslugiwany wyjatek podczas przetwarzania zadania (reference=%s)",
        reference,
        extra={"correlation_id": reference},
    )
    # The full exception chain (including the exception type) is logged
    # server-side with the correlation ID. The client always receives a
    # generic message - never the exception type, message, stack trace or
    # internal paths - to avoid leaking internal naming/structure even in DEBUG.
    message = _GENERIC_SERVER_ERROR
    return build_error_response(message, reference, status_code=500)


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handler for Starlette/FastAPI HTTPException.

    Preserves the original status code and detail but normalizes the response
    shape to {"error", "reference"} and attaches the correlation ID.
    """
    reference = _get_correlation_id(request)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return build_error_response(detail, reference, status_code=exc.status_code)


async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for request validation errors (422).

    Returns a sanitized message without echoing the raw validation context.
    """
    reference = _get_correlation_id(request)
    return build_error_response("Nieprawidlowe dane zadania.", reference, status_code=422)


def register_exception_handlers(app: object) -> None:
    """Register all centralized exception handlers and the correlation middleware."""
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        return
    # Correlation ID middleware must run inside the exception-handling scope.
    app.middleware("http")(correlation_id_middleware)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)  # type: ignore[arg-type]
