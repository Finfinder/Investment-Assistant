"""Structured JSON logging configuration for production and human-readable for development."""

import logging
import sys
from typing import Any

from app.core.config import get_settings

# Keys that must never appear in log output
_SENSITIVE_KEYS = frozenset({
    "password", "secret", "token", "api_key", "apikey",
    "authorization", "cookie", "credit_card",
})


class JSONFormatter(logging.Formatter):
    """Outputs one JSON object per log line — no sensitive data."""

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import UTC, datetime

        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = self.formatException(record.exc_info)
        # Strip sensitive data
        msg_lower = payload["message"].lower()
        for key in _SENSITIVE_KEYS:
            if key in msg_lower:
                payload["message"] = "[REDACTED — contains sensitive key]"
                break
        return json.dumps(payload, ensure_ascii=False)


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

    if settings.DEBUG:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s")
        )
    else:
        handler.setFormatter(JSONFormatter())

    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "yfinance", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
