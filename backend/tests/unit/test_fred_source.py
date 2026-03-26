"""Tests for FRED data source."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.modules.fundamental_analysis.data_sources.fred_source import FredSource


@pytest.fixture
def fred_source():
    return FredSource(api_key="test-key")


class TestFredSourceSuccess:
    def test_fetch_series_returns_latest_value(self, fred_source: FredSource):
        mock_series = pd.Series([5.25, 5.33, 5.50])
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = mock_series
        fred_source._fred = mock_fred

        result = fred_source.fetch_series("FEDFUNDS")
        assert result == 5.50
        mock_fred.get_series.assert_called_once()

    def test_fetch_indicator_maps_name_to_series(self, fred_source: FredSource):
        mock_series = pd.Series([3.5])
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = mock_series
        fred_source._fred = mock_fred

        result = fred_source.fetch_indicator("fed_funds_rate")
        assert result == 3.5
        # Verify the series ID was mapped correctly
        call_args = mock_fred.get_series.call_args
        assert call_args[0][0] == "FEDFUNDS"

    def test_fetch_multiple_returns_dict(self, fred_source: FredSource):
        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = [
            pd.Series([5.25]),
            pd.Series([300.0]),
        ]
        fred_source._fred = mock_fred

        result = fred_source.fetch_multiple(["fed_funds_rate", "cpi_us"])
        assert result["fed_funds_rate"] == 5.25
        assert result["cpi_us"] == 300.0


class TestFredSourceErrors:
    def test_fetch_series_returns_none_on_empty_data(self, fred_source: FredSource):
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = pd.Series(dtype=float)
        fred_source._fred = mock_fred

        result = fred_source.fetch_series("FEDFUNDS")
        assert result is None

    def test_fetch_indicator_returns_none_for_unknown_name(self, fred_source: FredSource):
        result = fred_source.fetch_indicator("nonexistent_indicator")
        assert result is None

    def test_fetch_series_returns_none_on_exception(self, fred_source: FredSource):
        mock_fred = MagicMock()
        mock_fred.get_series.side_effect = RuntimeError("API down")
        fred_source._fred = mock_fred

        result = fred_source.fetch_series("FEDFUNDS")
        assert result is None


class TestFredSourceCaching:
    def test_cached_value_is_returned_without_api_call(self, fred_source: FredSource):
        mock_fred = MagicMock()
        mock_fred.get_series.return_value = pd.Series([5.25])
        fred_source._fred = mock_fred

        # First call hits API
        result1 = fred_source.fetch_series("FEDFUNDS")
        assert result1 == 5.25
        assert mock_fred.get_series.call_count == 1

        # Second call should use cache
        result2 = fred_source.fetch_series("FEDFUNDS")
        assert result2 == 5.25
        assert mock_fred.get_series.call_count == 1  # no additional call
