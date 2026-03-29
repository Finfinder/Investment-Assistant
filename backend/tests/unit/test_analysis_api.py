"""Tests for api/v1/analysis.py"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.models import AnalysisReport, AnalysisStatusType, Timeframe
from app.modules.pipeline import analysis_tasks


@pytest.fixture(autouse=True)
def _clean_tasks():
    analysis_tasks.clear()
    yield
    analysis_tasks.clear()


@pytest.mark.asyncio
async def test_trigger_analysis(client):
    """POST /api/v1/analysis triggers pipeline and returns analysis_id."""
    with patch(
        "app.api.v1.analysis._run_pipeline",
        new_callable=AsyncMock,
    ):
        resp = await client.post("/api/v1/analysis", json={"symbol": "EURUSD", "timeframe": "H1"})

    assert resp.status_code == 200
    data = resp.json()
    assert "analysis_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_trigger_analysis_invalid_symbol(client):
    """POST with invalid symbol returns 400."""
    resp = await client.post("/api/v1/analysis", json={"symbol": "!!!!", "timeframe": "H1"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_analysis_not_found(client):
    """GET non-existent analysis returns 404."""
    resp = await client.get("/api/v1/analysis/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_analysis_status(client):
    """GET /api/v1/analysis/{id}/status returns status."""
    from app.core.models import AnalysisStatus

    analysis_tasks["test-id"] = AnalysisStatus(
        id="test-id",
        status=AnalysisStatusType.RUNNING,
        progress_pct=50.0,
        current_step="Analiza techniczna",
        steps_completed=["Pobieranie danych"],
    )

    resp = await client.get("/api/v1/analysis/test-id/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "test-id"
    assert data["status"] == "running"
    assert data["progress_pct"] == 50.0


@pytest.mark.asyncio
async def test_get_analysis_status_not_found(client):
    """GET /api/v1/analysis/{id}/status for non-existent returns 404."""
    resp = await client.get("/api/v1/analysis/missing/status")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Race condition / DB fallback tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_analysis_returns_report_after_completion(client):
    """GET /analysis/{id} returns AnalysisReport (not AnalysisStatus) when completed."""
    from app.api.v1.analysis import _analysis_results
    from app.core.models import AnalysisStatus

    report = AnalysisReport(symbol="EURUSD", timeframe=Timeframe.H1)
    analysis_tasks["done-id"] = AnalysisStatus(
        id="done-id",
        status=AnalysisStatusType.COMPLETED,
        progress_pct=100.0,
    )
    _analysis_results["done-id"] = report

    try:
        resp = await client.get("/api/v1/analysis/done-id")
        assert resp.status_code == 200
        data = resp.json()
        assert "symbol" in data
        assert data["symbol"] == "EURUSD"
    finally:
        _analysis_results.pop("done-id", None)


@pytest.mark.asyncio
async def test_get_analysis_db_fallback(client):
    """When report is not in cache but exists in DB, get_analysis returns it."""
    from app.core.models import AnalysisStatus

    report = AnalysisReport(symbol="GBPUSD", timeframe=Timeframe.H4)
    analysis_tasks["db-id"] = AnalysisStatus(
        id="db-id",
        status=AnalysisStatusType.COMPLETED,
        progress_pct=100.0,
    )

    mock_row = MagicMock()
    mock_row.result_json = report.model_dump_json()

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=mock_row)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_session)

    with patch("app.api.v1.analysis.get_session_factory", return_value=mock_factory):
        resp = await client.get("/api/v1/analysis/db-id")

    assert resp.status_code == 200
    data = resp.json()
    assert "symbol" in data
    assert data["symbol"] == "GBPUSD"


@pytest.mark.asyncio
async def test_get_analysis_db_fallback_graceful_on_missing_table(client):
    """DB fallback doesn't raise when the table is missing — returns AnalysisStatus."""
    from app.core.models import AnalysisStatus

    analysis_tasks["no-table-id"] = AnalysisStatus(
        id="no-table-id",
        status=AnalysisStatusType.COMPLETED,
        progress_pct=100.0,
    )

    with patch("app.api.v1.analysis.get_session_factory", side_effect=Exception("no such table")):
        resp = await client.get("/api/v1/analysis/no-table-id")

    assert resp.status_code == 200
    data = resp.json()
    # Should return AnalysisStatus (no 'symbol' field) since DB fallback failed gracefully
    assert "status" in data
    assert data["status"] == "completed"
