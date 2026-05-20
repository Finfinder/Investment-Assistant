"""Tests for calibration runner report payload."""

import argparse
import logging
from pathlib import Path
from typing import Any

import pytest
from scripts.calibrate_signal_thresholds import (
    CONFIG,
    CalibrationRunner,
    _build_runtime_config,
    _detect_and_score_patterns_for_window,
)

from app.core.models import Direction, OHLCVData, PatternDetection
from app.modules.signal_aggregation.threshold_calibration import TransactionOutcome
from tests.helpers import make_ohlcv


async def test_run_simple_stub_includes_config_version_and_period() -> None:
    runner = CalibrationRunner()

    report = await runner.run_simple_stub()

    configuration = report["configuration"]
    assert configuration["config_version"] == CONFIG["config_version"]
    assert configuration["period"] == {
        "start": "synthetic",
        "end": "synthetic",
        "mode": "mvp_stub",
    }
    assert configuration["mode"] == "synthetic_stub"
    assert configuration["symbols"] == CONFIG["symbols"]
    assert configuration["timeframes"] == CONFIG["timeframes"]
    assert len(report["candidates"]) == len(CONFIG["candidate_pairs"])
    assert report["recommendation"]["action"] in {
        "keep_current_thresholds",
        "consider_threshold_change",
    }
    assert report["recommendation"]["symmetry"] == "symmetric"


async def test_baseline_is_selected_by_threshold_values_not_index() -> None:
    custom_config = dict(CONFIG)
    custom_config["candidate_pairs"] = [
        (0.25, -0.25),
        (0.10, -0.10),
        (0.15, -0.15),
    ]

    runner = CalibrationRunner(config=custom_config)
    report = await runner.run_simple_stub()

    baseline = report["baseline"]
    assert baseline["bullish_threshold"] == pytest.approx(0.15)
    assert baseline["bearish_threshold"] == pytest.approx(-0.15)


async def test_build_runtime_config_uses_symbol_list_and_overrides_metadata(tmp_path: Path) -> None:
    symbol_list = tmp_path / "basket.txt"
    symbol_list.write_text("EUR/USD\nGC=F\n")
    args = argparse.Namespace(
        symbol=None,
        symbol_list=str(symbol_list),
        timeframe=["H1", "D1"],
        period_start="2025-01-01",
        period_end="2025-12-31",
        training_window_size=150,
        forward_window_size=30,
        step_size=10,
        output="report.json",
        verbose=False,
    )

    runtime_config = await _build_runtime_config(args)

    assert runtime_config["symbols"] == ["EUR/USD", "GC=F"]
    assert runtime_config["timeframes"] == ["H1", "D1"]
    assert runtime_config["period"] == {
        "start": "2025-01-01",
        "end": "2025-12-31",
        "mode": "mvp_stub",
    }
    assert runtime_config["training_window_size"] == 150
    assert runtime_config["forward_window_size"] == 30
    assert runtime_config["step_size"] == 10


async def test_run_simple_stub_warns_when_samples_below_min(caplog: pytest.LogCaptureFixture) -> None:
    config = dict(CONFIG)
    config["min_samples"] = 100  # Synthetic data generates only 17 samples

    runner = CalibrationRunner(config=config)
    with caplog.at_level(logging.WARNING, logger="scripts.calibrate_signal_thresholds"):
        report = await runner.run_simple_stub()

    assert "recommendation" in report  # Report still generated
    assert any("below minimum required" in record.message for record in caplog.records)


def test_detect_and_score_patterns_for_window_uses_pattern_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.modules.pattern_recognition.candlestick as candlestick_module
    import app.modules.pattern_recognition.chart_patterns as chart_patterns_module
    import app.modules.pattern_recognition.fibonacci as fibonacci_module
    import app.modules.pattern_recognition.iki_detector as iki_module
    import app.modules.pattern_recognition.relevance_scorer as relevance_module
    import app.modules.pattern_recognition.support_resistance as support_resistance_module

    first_pattern = PatternDetection(pattern_type="Hammer", confidence=0.8, bullish=True, detected_at_index=0)
    second_pattern = PatternDetection(pattern_type="Triangle", confidence=0.7, bullish=False, detected_at_index=2)
    ohlcv = [make_ohlcv(100 + i, 101 + i, 99 + i, 100.5 + i, index=i) for i in range(4)]
    score_calls: dict[str, float | int | bool] = {"target_called": False, "score_called": False}

    monkeypatch.setattr(candlestick_module, "detect_candlestick_patterns", lambda _ohlcv: [first_pattern])
    monkeypatch.setattr(support_resistance_module, "detect_support_resistance", lambda _ohlcv: [])
    monkeypatch.setattr(fibonacci_module, "calculate_fibonacci_levels", lambda _ohlcv: [])
    monkeypatch.setattr(chart_patterns_module, "detect_chart_patterns", lambda _ohlcv: [second_pattern])
    monkeypatch.setattr(iki_module, "detect_iki_pattern", lambda _ohlcv: [])

    def fake_calculate_target_prices(patterns: list[PatternDetection], _ohlcv: list[OHLCVData]) -> None:
        score_calls["target_called"] = True
        patterns[0].target_price = 123.45

    def fake_score_patterns(patterns: list[PatternDetection], total_candles: int, current_price: float = 0.0) -> None:
        score_calls["score_called"] = True
        score_calls["total_candles"] = total_candles
        score_calls["current_price"] = current_price
        patterns[0].relevance_score = 0.2
        patterns[1].relevance_score = 0.9

    monkeypatch.setattr(relevance_module, "calculate_target_prices", fake_calculate_target_prices)
    monkeypatch.setattr(relevance_module, "score_patterns", fake_score_patterns)

    patterns = _detect_and_score_patterns_for_window(ohlcv, "D1")

    assert score_calls["target_called"] is True
    assert score_calls["score_called"] is True
    assert score_calls["total_candles"] == 4
    assert score_calls["current_price"] == pytest.approx(float(ohlcv[-1].close))
    assert [pattern.pattern_type for pattern in patterns] == ["Triangle", "Hammer"]
    assert all(pattern.timeframe == "D1" for pattern in patterns)
    assert patterns[0].detected_at_timestamp == ohlcv[2].timestamp.isoformat()


async def test_run_with_real_data_builds_real_report_without_live_api(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.calibrate_signal_thresholds as calibration_module

    import app.modules.data_acquisition.providers.yfinance_provider as yfinance_module
    import app.modules.signal_aggregation.scoring as scoring_module
    import app.modules.signal_aggregation.threshold_calibration as threshold_calibration_module
    import app.modules.strategy_generator.sl_tp_calculator as sl_tp_module
    import app.modules.technical_analysis.indicators as indicators_module
    import app.modules.technical_analysis.moving_averages as moving_averages_module

    captured: dict[str, int | float | str] = {}
    ohlcv = [make_ohlcv(100 + i, 101 + i, 99 + i, 100.5 + i, index=i) for i in range(6)]

    class FakeProvider:
        async def fetch_ohlcv(self, symbol: str, timeframe: Any, period: str) -> list[OHLCVData]:
            captured["symbol"] = symbol
            captured["timeframe"] = str(timeframe)
            captured["period"] = period
            return ohlcv

    def fake_detect_patterns(training_window: list[OHLCVData], timeframe: str) -> list[PatternDetection]:
        captured["pattern_window_size"] = len(training_window)
        captured["pattern_timeframe"] = timeframe
        return [PatternDetection(pattern_type="Hammer", confidence=0.8, bullish=True, relevance_score=0.7)]

    def fake_calculate_indicators(training_window: list[OHLCVData], _params: Any) -> list[Any]:
        captured["indicator_window_size"] = len(training_window)
        return []

    def fake_calculate_moving_averages(training_window: list[OHLCVData]) -> list[Any]:
        captured["moving_average_window_size"] = len(training_window)
        return []

    def fake_calculate_weighted_score(_aggregator: Any, weights: dict[str, float] | None = None) -> float:
        captured["custom_weights_used"] = "yes" if weights is not None else "no"
        return 0.22

    def fake_calculate_sl_tp(
        training_window: list[OHLCVData],
        direction: Direction,
        entry: float,
        support_resistance: list[PatternDetection] | None = None,
    ) -> dict[str, float]:
        captured["sl_tp_window_size"] = len(training_window)
        captured["entry_price"] = entry
        captured["direction"] = direction
        captured["sr_count"] = len(support_resistance or [])
        return {"stop_loss": entry - 1.0, "tp1": entry + 1.0}

    def fake_label_signal_outcome(
        direction: Direction | None,
        entry_price: float | None,
        stop_loss: float | None,
        tp1: float | None,
        future_ohlcv: list[OHLCVData],
    ) -> TransactionOutcome:
        captured["future_window_size"] = len(future_ohlcv)
        assert direction == Direction.LONG
        assert entry_price is not None
        assert stop_loss is not None
        assert tp1 is not None
        return TransactionOutcome.TP_BEFORE_SL

    monkeypatch.setattr(yfinance_module, "YFinanceProvider", FakeProvider)
    monkeypatch.setattr(calibration_module, "_detect_and_score_patterns_for_window", fake_detect_patterns)
    monkeypatch.setattr(indicators_module, "calculate_indicators", fake_calculate_indicators)
    monkeypatch.setattr(moving_averages_module, "calculate_moving_averages", fake_calculate_moving_averages)
    monkeypatch.setattr(scoring_module, "calculate_weighted_score", fake_calculate_weighted_score)
    monkeypatch.setattr(sl_tp_module, "calculate_sl_tp", fake_calculate_sl_tp)
    monkeypatch.setattr(threshold_calibration_module, "label_signal_outcome", fake_label_signal_outcome)

    runner = CalibrationRunner(
        config={
            "symbols": ["^GSPC"],
            "timeframes": ["D1"],
            "training_window_size": 3,
            "forward_window_size": 2,
            "step_size": 1,
            "period": {"start": "2024-01-01", "end": "2024-12-31", "mode": "cli_override"},
            "candidate_pairs": [(0.15, -0.15)],
        }
    )

    report = await runner.run_with_real_data()

    assert captured["symbol"] == "^GSPC"
    assert captured["period"] == "5y"
    assert captured["pattern_window_size"] == 3
    assert captured["indicator_window_size"] == 3
    assert captured["moving_average_window_size"] == 3
    assert captured["sl_tp_window_size"] == 3
    assert captured["sr_count"] == 0
    assert captured["future_window_size"] == 2
    assert captured["pattern_timeframe"] == "D1"
    assert captured["custom_weights_used"] == "no"
    assert report["configuration"]["mode"] == "real_data"
    assert report["configuration"]["period"]["mode"] == "real_data"
    assert report["configuration"]["period"]["start"] == "2024-01-01"
    assert report["configuration"]["period"]["end"] == "2024-12-31"
    assert report["configuration"]["period"]["per_timeframe_window"] == {"D1": "5y"}
    assert "Results are from synthetic training data." not in report["limitations"]
    assert report["baseline"]["bullish_threshold"] == pytest.approx(0.15)
    assert report["baseline"]["long_signals"] == 2
