"""Shared validation utilities for API v1 endpoints."""

import re

from fastapi import HTTPException

# Canonical symbol pattern: alphanumeric, slash, hyphen (2-20 chars).
# Covers forex pairs (EUR/USD), commodities (XAUUSD), indices (US500).
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9/\-]{2,20}$")

# Period format: 1-4 digits followed by d/m/y (e.g. 30d, 6m, 1y).
PERIOD_PATTERN = re.compile(r"^\d{1,4}[dymDYM]$")


def validate_symbol(symbol: str) -> None:
    """Raise HTTP 400 if symbol format is invalid."""
    if not SYMBOL_PATTERN.match(symbol):
        raise HTTPException(status_code=400, detail="Invalid symbol format")


def validate_period(period: str) -> None:
    """Raise HTTP 400 if period format is invalid."""
    if not PERIOD_PATTERN.match(period):
        raise HTTPException(status_code=400, detail="Invalid period format (e.g. 30d, 6m, 1y)")
