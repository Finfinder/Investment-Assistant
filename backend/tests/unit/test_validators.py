"""Tests for API v1 validation utilities."""

import pytest
from fastapi import HTTPException

from app.api.v1.validators import validate_analysis_id, validate_period, validate_symbol


class TestValidateSymbol:
    """Tests for symbol validation."""

    def test_valid_forex_pair(self) -> None:
        """Valid forex pair should not raise."""
        validate_symbol("EUR/USD")
        validate_symbol("GBP/USD")
        validate_symbol("USD/JPY")

    def test_valid_commodity(self) -> None:
        """Valid commodity symbol should not raise."""
        validate_symbol("XAUUSD")
        validate_symbol("XAG/USD")

    def test_valid_index(self) -> None:
        """Valid index symbol should not raise."""
        validate_symbol("US500")
        validate_symbol("NAS100")

    def test_valid_with_hyphen(self) -> None:
        """Valid symbol with hyphen should not raise."""
        validate_symbol("BTC-USD")
        validate_symbol("ETH-USD")

    def test_invalid_too_short(self) -> None:
        """Symbol too short should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_symbol("E")
        assert exc_info.value.status_code == 400
        assert "Invalid symbol format" in exc_info.value.detail

    def test_invalid_too_long(self) -> None:
        """Symbol too long should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_symbol("A" * 21)
        assert exc_info.value.status_code == 400

    def test_invalid_special_chars(self) -> None:
        """Symbol with special characters should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_symbol("EURUSD!")
        assert exc_info.value.status_code == 400

    def test_invalid_empty(self) -> None:
        """Empty symbol should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_symbol("")
        assert exc_info.value.status_code == 400


class TestValidatePeriod:
    """Tests for period validation."""

    def test_valid_days(self) -> None:
        """Valid day period should not raise."""
        validate_period("1d")
        validate_period("30d")
        validate_period("365d")

    def test_valid_months(self) -> None:
        """Valid month period should not raise."""
        validate_period("1m")
        validate_period("6m")
        validate_period("24m")

    def test_valid_years(self) -> None:
        """Valid year period should not raise."""
        validate_period("1y")
        validate_period("5y")
        validate_period("10y")

    def test_valid_uppercase(self) -> None:
        """Valid period with uppercase should not raise."""
        validate_period("30D")
        validate_period("6M")
        validate_period("1Y")

    def test_invalid_format(self) -> None:
        """Invalid period format should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_period("30days")
        assert exc_info.value.status_code == 400
        assert "Invalid period format" in exc_info.value.detail

    def test_invalid_empty(self) -> None:
        """Empty period should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_period("")
        assert exc_info.value.status_code == 400


class TestValidateAnalysisId:
    """Tests for analysis_id UUID4 validation."""

    def test_valid_uuid4(self) -> None:
        """Valid UUID4 should not raise."""
        # UUID4 format: 8-4-4-4-12, with version 4 (4 in 3rd group)
        validate_analysis_id("550e8400-e29b-41d4-a716-446655440000")
        validate_analysis_id("123e4567-e89b-41d3-a456-426614174000")
        validate_analysis_id("a1b2c3d4-5678-4abc-9def-0123456789ab")

    def test_invalid_uuid3(self) -> None:
        """UUID3 should raise 400 (wrong version)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_analysis_id("550e8400-e29b-31d4-a716-446655440000")
        assert exc_info.value.status_code == 400
        assert "Invalid analysis ID format" in exc_info.value.detail

    def test_invalid_uuid1(self) -> None:
        """UUID1 should raise 400 (wrong version)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_analysis_id("550e8400-e29b-11d4-a716-446655440000")
        assert exc_info.value.status_code == 400

    def test_invalid_format(self) -> None:
        """Invalid UUID format should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_analysis_id("not-a-uuid")
        assert exc_info.value.status_code == 400

    def test_invalid_empty(self) -> None:
        """Empty analysis_id should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            validate_analysis_id("")
        assert exc_info.value.status_code == 400

    def test_invalid_uppercase(self) -> None:
        """UUID with uppercase should raise 400 (lowercase required)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_analysis_id("550E8400-E29B-41D4-A716-446655440000")
        assert exc_info.value.status_code == 400
