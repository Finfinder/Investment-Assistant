"""Tests for the shared mutation score threshold resolution in run_mutmut.py."""

import json

from scripts import run_mutmut


def _shared_threshold() -> int:
    """Read the expected threshold from the single source of truth."""
    with run_mutmut.THRESHOLD_FILE.open(encoding="utf-8") as fh:
        return int(json.load(fh)["mutationScoreThreshold"])


def test_load_default_min_score_reads_shared_file(monkeypatch):
    """Without env override, the threshold comes from mutation-threshold.json."""
    monkeypatch.delenv("MUTATION_SCORE_THRESHOLD", raising=False)
    assert run_mutmut.load_default_min_score() == _shared_threshold()


def test_load_default_min_score_env_override(monkeypatch):
    """MUTATION_SCORE_THRESHOLD takes priority over the shared file."""
    monkeypatch.setenv("MUTATION_SCORE_THRESHOLD", "85")
    assert run_mutmut.load_default_min_score() == 85


def test_load_default_min_score_env_invalid_falls_back_to_file(monkeypatch):
    """An invalid env value falls back to the shared file value."""
    monkeypatch.setenv("MUTATION_SCORE_THRESHOLD", "not-a-number")
    assert run_mutmut.load_default_min_score() == _shared_threshold()


def test_load_default_min_score_missing_file_falls_back(monkeypatch):
    """When the shared file is missing, the fallback value (70) is used."""
    monkeypatch.delenv("MUTATION_SCORE_THRESHOLD", raising=False)
    monkeypatch.setattr(run_mutmut, "THRESHOLD_FILE", run_mutmut.Path("/nonexistent/mutation-threshold.json"))
    assert run_mutmut.load_default_min_score() == run_mutmut.FALLBACK_MIN_SCORE


def test_threshold_file_path_points_to_repo_root():
    """The threshold file must live at the repository root (two levels above scripts)."""
    expected = run_mutmut.Path(__file__).resolve().parents[3] / "mutation-threshold.json"
    assert expected == run_mutmut.THRESHOLD_FILE
    assert run_mutmut.THRESHOLD_FILE.exists()
