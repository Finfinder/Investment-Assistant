"""Reusable daily rate limiter for external API providers."""

from datetime import UTC, datetime


class DailyRateLimiter:
    """Tracks daily request count and resets at UTC midnight."""

    def __init__(self, limit: int, provider_name: str) -> None:
        self._limit = limit
        self._provider_name = provider_name
        self._request_count = 0
        self._count_reset_date: str = datetime.now(UTC).strftime("%Y-%m-%d")

    def check(self) -> None:
        """Raise RuntimeError if the daily limit has been exceeded."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if today != self._count_reset_date:
            self._request_count = 0
            self._count_reset_date = today

        if self._request_count >= self._limit:
            raise RuntimeError(f"{self._provider_name} daily rate limit ({self._limit}) exceeded")

    def increment(self) -> None:
        """Record one request."""
        self._request_count += 1
