"""Structured JSON logging configuration for production and human-readable for development."""

import contextvars
import logging
import sys
from typing import Any

from app.core.config import get_settings

# Context variable carrying the per-request correlation ID into log records.
# Set by the correlation-ID middleware in ``app.core.errors`` and injected into
# every log record by ``CorrelationIdFilter`` so all logs during a request are
# correlated without passing the ID through every call site.
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)

# Keys that must never appear in log output
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "credit_card",
        "twelve_data_api_key",
        "fmp_api_key",
        "fred_api_key",
        "redis_password",
        "database_url",
    }
)


class JSONFormatter(logging.Formatter):
    """Outputs one JSON object per log line - no sensitive data."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import UTC, datetime

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self._sanitize(str(self.formatException(record.exc_info)))
        # Sanitize message
        payload["message"] = self._sanitize(payload["message"])
        # Sanitize record.args (W5: CWE-532)
        # Note: dict args (%-style logging) must be handled separately -
        # iterating a dict yields only keys, which would silently drop values
        # and bypass sanitization of sensitive data.
        if record.args:
            if isinstance(record.args, dict):
                safe_args: dict[str, str] | tuple[str, ...] = {
                    k: self._sanitize(str(v)) for k, v in record.args.items()
                }
            else:
                safe_args = tuple(self._sanitize(str(arg)) for arg in record.args)
            payload["args"] = safe_args
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _sanitize(text: str) -> str:
        """Redact sensitive keys from text."""
        text_lower = text.lower()
        for key in _SENSITIVE_KEYS:
            if key in text_lower:
                return "[REDACTED - contains sensitive key]"
        return text


class SensitiveFilter(logging.Formatter):
    """Human-readable formatter that redacts sensitive data (used in DEBUG mode)."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        msg_lower = message.lower()
        for key in _SENSITIVE_KEYS:
            if key in msg_lower:
                return "[REDACTED - contains sensitive key]"
        return message


class CorrelationIdFilter(logging.Filter):
    """Inject the per-request correlation ID into every log record.

    Reads the value from ``correlation_id_var`` (set by the correlation-ID
    middleware) so that logs emitted anywhere during a request carry the same
    correlation ID, enabling end-to-end tracing without threading the ID
    through every call site.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def setup_logging() -> None:
    """Configure root logger based on settings."""
    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.addFilter(CorrelationIdFilter())

    if settings.DEBUG:
        handler.setFormatter(SensitiveFilter(fmt="%(asctime)s %(levelname)-8s %(name)s - %(message)s"))
    else:
        handler.setFormatter(JSONFormatter())

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "yfinance", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
