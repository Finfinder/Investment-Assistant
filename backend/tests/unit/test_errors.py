"""Unit tests for centralized error handling and correlation IDs."""

import logging
from unittest.mock import MagicMock, patch

from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import errors
from app.core.errors import (
    build_error_response,
    correlation_id_middleware,
    register_exception_handlers,
)
from app.core.logging_config import CorrelationIdFilter, correlation_id_var


def _mock_request(correlation_id: str = "abc123") -> MagicMock:
    request = MagicMock()
    request.state.correlation_id = correlation_id
    return request


class TestBuildErrorResponse:
    def test_response_shape_and_status(self) -> None:
        resp = build_error_response("Cos poszlo nie tak", "ref-1", status_code=500)
        assert resp.status_code == 500
        assert resp.body  # non-empty
        import json

        data = json.loads(resp.body)
        assert data == {"error": "Cos poszlo nie tak", "reference": "ref-1"}

    def test_response_never_contains_traceback(self) -> None:
        import json

        resp = build_error_response("err", "ref", status_code=500)
        body = json.loads(resp.body)
        assert "Traceback" not in body["error"]
        assert "/" not in body["reference"]


class TestCorrelationIdMiddleware:
    async def test_assigns_correlation_id_and_propagates(self) -> None:
        captured: dict[str, object] = {}

        async def call_next(request):  # type: ignore[no-untyped-def]
            captured["correlation_id"] = request.state.correlation_id
            from starlette.responses import Response

            return Response(content="ok")

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        from starlette.requests import Request

        request = Request(scope)
        result = await correlation_id_middleware(request, call_next)
        assert result.status_code == 200
        assert isinstance(captured["correlation_id"], str)
        assert len(captured["correlation_id"]) == 32  # uuid4().hex
        # Correlation ID echoed back to the client.
        assert result.headers["X-Request-ID"] == captured["correlation_id"]

    async def test_correlation_id_reset_after_request(self) -> None:
        async def call_next(_: object):
            from starlette.responses import Response

            return Response(content="ok")

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
        }
        from starlette.requests import Request

        request = Request(scope)
        await correlation_id_middleware(request, call_next)
        # Context variable must be reset after the request completes.
        assert errors.correlation_id_var.get() is None


class TestUnhandledExceptionHandler:
    async def test_logs_full_chain_and_returns_sanitized_response_prod(self) -> None:
        with patch.object(errors.logger, "exception") as mock_log:
            request = _mock_request("ref-prod")
            exc = ValueError("root cause detail with /internal/path")

            resp = await errors._unhandled_exception_handler(request, exc)
            assert resp.status_code == 500
            import json

            data = json.loads(resp.body)
            assert data["reference"] == "ref-prod"
            assert "root cause" not in data["error"]
            assert "/" not in data["error"]
            mock_log.assert_called_once()

    async def test_debug_mode_returns_generic_message_not_internal_details(self) -> None:
        with patch.object(errors.logger, "exception"):
            request = _mock_request("ref-debug")
            exc = RuntimeError("secret/internal/path/traceback")
            resp = await errors._unhandled_exception_handler(request, exc)
            import json

            data = json.loads(resp.body)
            assert data["reference"] == "ref-debug"
            # Even in DEBUG, the exception type and message must not leak.
            assert "RuntimeError" not in data["error"]
            assert "secret" not in data["error"]
            assert "traceback" not in data["error"]
            assert data["error"] == errors._GENERIC_SERVER_ERROR


class TestHttpExceptionHandler:
    async def test_preserves_status_and_detail_shape(self) -> None:
        request = _mock_request("ref-http")
        exc = StarletteHTTPException(status_code=404, detail="Nie znaleziono")
        resp = await errors._http_exception_handler(request, exc)
        assert resp.status_code == 404
        import json

        data = json.loads(resp.body)
        assert data == {"error": "Nie znaleziono", "reference": "ref-http"}


class TestValidationExceptionHandler:
    async def test_returns_422_sanitized(self) -> None:
        from fastapi.exceptions import RequestValidationError

        request = _mock_request("ref-val")
        exc = RequestValidationError(errors=[])
        resp = await errors._validation_exception_handler(request, exc)
        assert resp.status_code == 422
        import json

        data = json.loads(resp.body)
        assert data["reference"] == "ref-val"
        assert "error" in data


class TestRegisterExceptionHandlers:
    def test_registers_handlers_on_fastapi_app(self) -> None:
        from fastapi import FastAPI

        app = MagicMock(spec=FastAPI)
        app.add_exception_handler = MagicMock()
        register_exception_handlers(app)
        assert app.add_exception_handler.call_count == 3


class TestCorrelationIdFilter:
    def test_filter_injects_contextvar_into_record(self) -> None:
        correlation_id_var.set("req-xyz")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        assert CorrelationIdFilter().filter(record) is True
        assert record.correlation_id == "req-xyz"
        correlation_id_var.set(None)

    def test_filter_defaults_to_none_when_unset(self) -> None:
        correlation_id_var.set(None)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        CorrelationIdFilter().filter(record)
        assert record.correlation_id is None

    def test_ignores_non_fastapi_app(self) -> None:
        register_exception_handlers(object())  # should not raise
