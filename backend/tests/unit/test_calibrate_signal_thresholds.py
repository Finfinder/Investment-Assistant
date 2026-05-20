"""Tests for calibration runner report payload."""

import argparse
import logging

import pytest
from scripts.calibrate_signal_thresholds import (
    CONFIG,
    CalibrationRunner,
    _build_runtime_config,
)


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


async def test_build_runtime_config_uses_symbol_list_and_overrides_metadata(tmp_path) -> None:
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


async def test_run_simple_stub_warns_when_samples_below_min(caplog) -> None:
    config = dict(CONFIG)
    config["min_samples"] = 100  # Synthetic data generates only 17 samples

    runner = CalibrationRunner(config=config)
    with caplog.at_level(logging.WARNING, logger="scripts.calibrate_signal_thresholds"):
        report = await runner.run_simple_stub()

    assert "recommendation" in report  # Report still generated
    assert any("below minimum required" in record.message for record in caplog.records)
