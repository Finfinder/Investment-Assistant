"""Tests for api/v1/analysis.py"""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.models import AnalysisStatusType
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
