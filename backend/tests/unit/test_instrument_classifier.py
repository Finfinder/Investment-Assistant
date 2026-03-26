"""Tests for core/instrument_classifier.py"""

from app.core.instrument_classifier import (
    COMMODITY_SYMBOLS,
    FOREX_PAIRS,
    INDEX_SYMBOLS,
    classify_instrument,
)
from app.core.models import InstrumentType


class TestClassifyInstrument:
    def test_forex_pair(self):
        assert classify_instrument("EURUSD") == InstrumentType.FOREX

    def test_forex_pair_with_slash(self):
        assert classify_instrument("EUR/USD") == InstrumentType.FOREX

    def test_forex_pair_lowercase(self):
        assert classify_instrument("eurusd") == InstrumentType.FOREX

    def test_forex_heuristic_6char(self):
        assert classify_instrument("ABCDEF") == InstrumentType.FOREX

    def test_commodity(self):
        assert classify_instrument("GOLD") == InstrumentType.COMMODITY

    def test_commodity_with_dash(self):
        assert classify_instrument("XAU-USD") == InstrumentType.COMMODITY

    def test_index(self):
        assert classify_instrument("US500") == InstrumentType.INDEX

    def test_unknown_returns_none(self):
        assert classify_instrument("UNKNOWN123") is None

    def test_all_forex_pairs_classified(self):
        for pair in FOREX_PAIRS:
            assert classify_instrument(pair) == InstrumentType.FOREX

    def test_all_commodity_symbols_classified(self):
        for symbol in COMMODITY_SYMBOLS:
            assert classify_instrument(symbol) == InstrumentType.COMMODITY

    def test_all_index_symbols_classified(self):
        for symbol in INDEX_SYMBOLS:
            assert classify_instrument(symbol) == InstrumentType.INDEX
