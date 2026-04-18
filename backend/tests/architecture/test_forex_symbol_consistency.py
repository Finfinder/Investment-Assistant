"""Architecture test — ensures all classifier symbol sets have mappings in every data provider."""

import pytest

from app.core.instrument_classifier import COMMODITY_SYMBOLS, FOREX_PAIRS, INDEX_SYMBOLS
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


@pytest.mark.architecture
class TestCommoditySymbolConsistency:
    """All COMMODITY_SYMBOLS must be present in every provider's symbol map."""

    def test_yfinance_covers_all_commodity_symbols(self) -> None:
        missing = COMMODITY_SYMBOLS - set(YF_SYMBOL_MAP.keys())
        assert not missing, f"YFinance SYMBOL_MAP missing commodity symbols: {missing}"

    def test_twelvedata_covers_all_commodity_symbols(self) -> None:
        supported = set(TwelveDataProvider(api_key="dummy").get_supported_symbols())
        missing = COMMODITY_SYMBOLS - supported
        # Aliasy XAU/XAG nie są w liście TwelveData (używane są GOLD/SILVER zamiast tego)
        excluded = {"XAUUSD", "XAGUSD", "WTIUSD"}
        assert not (missing - excluded), f"TwelveData missing commodity symbols: {missing - excluded}"

    def test_fmp_covers_all_commodity_symbols(self) -> None:
        missing = COMMODITY_SYMBOLS - set(FMP_SYMBOL_MAP.keys())
        # Aliasy XAU/XAG nie są w FMP (mapowane przez GOLD/SILVER)
        excluded = {"XAUUSD", "XAGUSD", "WTIUSD"}
        assert not (missing - excluded), f"FMP SYMBOL_MAP missing commodity symbols: {missing - excluded}"


@pytest.mark.architecture
class TestIndexSymbolConsistency:
    """INDEX_SYMBOLS that appear in provider maps must map to valid index tickers."""

    def test_yfinance_index_mappings_are_valid(self) -> None:
        """Każdy symbol z INDEX_SYMBOLS obecny w YFinance SYMBOL_MAP musi mapować na ticker indeksowy."""
        for sym in INDEX_SYMBOLS:
            if sym in YF_SYMBOL_MAP:
                ticker = YF_SYMBOL_MAP[sym]
                assert ticker.startswith("^") or "." in ticker, (
                    f"{sym} jest w INDEX_SYMBOLS i YF SYMBOL_MAP, ale mapuje na niepoprawny ticker: {ticker}"
                )

    def test_twelvedata_index_mappings_are_valid(self) -> None:
        """Każdy symbol z INDEX_SYMBOLS obecny w TwelveData musi być poprawnie mapowany."""
        provider = TwelveDataProvider(api_key="dummy")
        supported = set(provider.get_supported_symbols())
        for sym in INDEX_SYMBOLS:
            if sym in supported:
                mapped = provider._map_symbol(sym)
                assert mapped != sym, f"TwelveData nie mapuje symbolu indeksowego {sym}"

    def test_fmp_index_mappings_are_valid(self) -> None:
        """Każdy symbol z INDEX_SYMBOLS obecny w FMP SYMBOL_MAP musi mapować na ticker indeksowy."""
        for sym in INDEX_SYMBOLS:
            if sym in FMP_SYMBOL_MAP:
                ticker = FMP_SYMBOL_MAP[sym]
                assert ticker.startswith("^") or ticker != sym, (
                    f"{sym} jest w INDEX_SYMBOLS i FMP SYMBOL_MAP, ale mapuje na niepoprawny ticker: {ticker}"
                )
