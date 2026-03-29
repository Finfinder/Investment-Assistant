"""Architecture test — ensures all FOREX_PAIRS have mappings in every data provider."""

import pytest

from app.core.instrument_classifier import FOREX_PAIRS
from app.modules.data_acquisition.providers.fmp_provider import SYMBOL_MAP as FMP_SYMBOL_MAP
from app.modules.data_acquisition.providers.twelve_data_provider import TwelveDataProvider
from app.modules.data_acquisition.providers.yfinance_provider import SYMBOL_MAP as YF_SYMBOL_MAP


@pytest.mark.architecture
class TestForexSymbolConsistency:
    """All FOREX_PAIRS must be present in every provider's symbol map."""

    def test_yfinance_covers_all_forex_pairs(self) -> None:
        yf_forex_keys = {k for k, v in YF_SYMBOL_MAP.items() if v.endswith("=X")}
        missing = FOREX_PAIRS - yf_forex_keys
        assert not missing, f"YFinance SYMBOL_MAP missing forex pairs: {missing}"

    def test_twelvedata_covers_all_forex_pairs(self) -> None:
        provider = TwelveDataProvider(api_key="dummy")
        missing = set()
        for pair in FOREX_PAIRS:
            mapped = provider._map_symbol(pair)
            if "/" not in mapped:
                missing.add(pair)
        assert not missing, f"TwelveData forex_pairs missing: {missing}"

    def test_fmp_covers_all_forex_pairs(self) -> None:
        fmp_keys = set(FMP_SYMBOL_MAP.keys())
        missing = FOREX_PAIRS - fmp_keys
        assert not missing, f"FMP SYMBOL_MAP missing forex pairs: {missing}"
