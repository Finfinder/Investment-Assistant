"""Structured JSON logging configuration for production and human-readable for development."""

import contextvars
import logging
import re
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

# Compiled once at import time - sanitize_log_message runs on every log message.
# Masks credentials embedded in URLs: redis://user:pass@host -> redis://user:***@host
# and redis://pass@host -> redis://***@host. Protocol-agnostic (any scheme
# ``xxx://``) to avoid regressions for non-listed protocols (e.g. mongodb, mysql)
# and tolerant of '/' or '@' inside the password. The username is preserved;
# only the password segment is masked. Splitting at the last '@' mirrors the
# original ``_mask_url`` rsplit semantics so a password containing '@' works.
_URL_CREDS_RE = re.compile(
    r"(?P<protocol>[a-zA-Z][a-zA-Z0-9+.\-]*)://"
    r"(?P<creds>(?:[^@\s]*@)*[^@\s]*)"  # user[:password] - may contain '/' or '@' in password; split at last '@'
    r"@"
)


def _mask_url_creds(match: re.Match[str]) -> str:
    """Build the masked URL replacement, preserving the username when present.

    Matches the original ``_mask_url`` semantics: ``redis://user:pass@host``
    keeps the username (``redis://user:***@host``), while ``redis://pass@host``
    (no colon, password-only) masks the whole credentials segment. A password
    containing '/' or '@' is handled by splitting credentials at the last ':'.
    """
    protocol = match.group("protocol")
    creds = match.group("creds")
    # Empty credentials (e.g. redis://@host) -> mask the whole segment.
    if not creds:
        return f"{protocol}://***@"
    # Split credentials at the last ':' to separate user from password.
    if ":" in creds:
        user, _ = creds.rsplit(":", 1)
        return f"{protocol}://{user}:***@"
    # No colon: password-only format (e.g. redis://password@host).
    return f"{protocol}://***@"


# Masks key=value / key: value pairs for sensitive keys (case-insensitive).
# For ``authorization: Bearer <token>`` the token after the space is also
# consumed so the credential value is not left exposed. The value class stops
# at whitespace and common delimiters (& quotes , ;) so masking preserves the
# rest of the message/URL (e.g. ``api_key=SECRET&series_id=FEDFUNDS`` keeps the
# ``&series_id=...`` suffix) - restoring the prior ``[^&\s"']+`` behaviour.
_KEY_VALUE_RE = re.compile(
    r"(?P<key>password|api_key|apikey|token|secret|credential|credentials|authorization|cookie)"
    r"\s*[=:]\s*(?:Bearer\s+)?[^\s&\"',;]+",
    re.IGNORECASE,
)

# Replacement marker keeps the structure of the message readable after masking.
_KEY_VALUE_REPL = r"\g<key>=***"


def sanitize_log_message(message: str) -> str:
    """Single entry point for value-masking sensitive data in log messages.

    Consolidates all sensitive-pattern *value* masking (URL credentials, API
    keys, tokens, passwords, connection strings) into one idempotent helper so
    new log statements cannot accidentally leak credential values.

    It masks the sensitive **value** while keeping the message structure
    readable (e.g. ``api_key=SECRET`` -> ``api_key=***``,
    ``redis://user:pass@host`` -> ``redis://user:***@host``). Whole-message
    redaction of messages that merely *name* a configuration key (e.g.
    ``Twelve_Data_API_Key is configured``) is performed by the log formatters
    (``JSONFormatter`` / ``SensitiveFilter``) on top of this helper, preserving
    the existing behaviour tested in ``test_main.py``.

    Idempotent: calling the helper twice yields the same result as once.
    """
    if not message:
        return message
    masked = _URL_CREDS_RE.sub(_mask_url_creds, message)
    return _KEY_VALUE_RE.sub(_KEY_VALUE_REPL, masked)


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
        """Value-mask then whole-message redact sensitive keys from text."""
        masked = sanitize_log_message(text)
        text_lower = masked.lower()
        for key in _SENSITIVE_KEYS:
            if key in text_lower:
                return "[REDACTED - contains sensitive key]"
        return masked


class SensitiveFilter(logging.Formatter):
    """Human-readable formatter that redacts sensitive data (used in DEBUG mode)."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        masked = sanitize_log_message(message)
        msg_lower = masked.lower()
        for key in _SENSITIVE_KEYS:
            if key in msg_lower:
                return "[REDACTED - contains sensitive key]"
        return masked


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
