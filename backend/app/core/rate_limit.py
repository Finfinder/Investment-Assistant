"""Application-wide rate limiter instance."""

from slowapi import Limiter

from app.core.client_identity import get_rate_limit_key

limiter = Limiter(key_func=get_rate_limit_key)
