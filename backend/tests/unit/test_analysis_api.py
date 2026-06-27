"""Tests for api/v1/analysis.py"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.models import AnalysisReport, AnalysisStatusType, Timeframe
from app.modules.pipeline import analysis_tasks

# Valid UUID4 constants for tests
_UUID_NONEXISTENT = "00000000-0000-4000-8000-000000000001"
_UUID_TEST = "00000000-0000-4000-8000-000000000002"
_UUID_MISSING = "00000000-0000-4000-8000-000000000003"
_UUID_DONE = "00000000-0000-4000-8000-000000000004"
_UUID_DB = "00000000-0000-4000-8000-000000000005"
_UUID_NO_TABLE = "00000000-0000-4000-8000-000000000006"


@pytest.fixture(autouse=True)
def _clean_tasks():
    analysis_tasks.clear()
    # Mock Redis with in-memory storage for RedisCache
    _redis_store: dict[str, bytes] = {}

    async def _mock_get(key):
        return _redis_store.get(key)

    async def _mock_setex(key, ttl, value):
        _redis_store[key] = value if isinstance(value, bytes) else value.encode()

    async def _mock_delete(key):
        _redis_store.pop(key, None)

    with patch("app.modules.data_acquisition.redis_cache.redis_manager") as mock_manager:
        mock_client = AsyncMock()
        mock_client.get = _mock_get
        mock_client.setex = _mock_setex
        mock_client.delete = _mock_delete
        mock_manager.client = mock_client
        yield
    analysis_tasks.clear()


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


async def test_trigger_analysis_invalid_symbol(client):
    """POST with invalid symbol returns 400."""
    resp = await client.post("/api/v1/analysis", json={"symbol": "!!!!", "timeframe": "H1"})
    assert resp.status_code == 400


async def test_trigger_analysis_duplicate_returns_409(client):
    """POST with duplicate analysis_id returns 409 Conflict."""
    from app.api.v1.analysis import _background_tasks

    # Pre-populate _background_tasks with a running task using known UUID
    # This simulates a race condition where the same analysis_id is already being processed
    _background_tasks[_UUID_TEST] = AsyncMock()

    # Mock AnalysisPipeline to return our known UUID
    mock_pipeline = MagicMock()
    mock_pipeline.analysis_id = _UUID_TEST

    with (
        patch("app.api.v1.analysis.AnalysisPipeline", return_value=mock_pipeline),
        patch("app.api.v1.analysis._run_pipeline", new_callable=AsyncMock),
    ):
        resp = await client.post("/api/v1/analysis", json={"symbol": "EURUSD", "timeframe": "H1"})

    assert resp.status_code == 409
    assert "already running" in resp.json()["detail"]
    # Clean up
    _background_tasks.pop(_UUID_TEST, None)


async def test_get_analysis_not_found(client):
    """GET non-existent analysis returns 404."""
    resp = await client.get(f"/api/v1/analysis/{_UUID_NONEXISTENT}")
    assert resp.status_code == 404


async def test_get_analysis_status(client):
    """GET /api/v1/analysis/{id}/status returns status."""
    from app.core.models import AnalysisStatus

    analysis_tasks[_UUID_TEST] = AnalysisStatus(
        id=_UUID_TEST,
        status=AnalysisStatusType.RUNNING,
        progress_pct=50.0,
        current_step="Analiza techniczna",
        steps_completed=["Pobieranie danych"],
    )

    resp = await client.get(f"/api/v1/analysis/{_UUID_TEST}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == _UUID_TEST
    assert data["status"] == "running"
    assert data["progress_pct"] == 50.0


async def test_get_analysis_status_not_found(client):
    """GET /api/v1/analysis/{id}/status for non-existent returns 404."""
    resp = await client.get(f"/api/v1/analysis/{_UUID_MISSING}/status")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Race condition / DB fallback tests
# ---------------------------------------------------------------------------


async def test_get_analysis_returns_report_after_completion(client):
    """GET /analysis/{id} returns AnalysisReport (not AnalysisStatus) when completed."""

    from app.api.v1.analysis import _analysis_results
    from app.core.models import AnalysisStatus

    report = AnalysisReport(symbol="EURUSD", timeframe=Timeframe.H1)
    analysis_tasks[_UUID_DONE] = AnalysisStatus(
        id=_UUID_DONE,
        status=AnalysisStatusType.COMPLETED,
        progress_pct=100.0,
    )
    report_data = report.model_dump(mode="json")
    await _analysis_results.set(_UUID_DONE, report_data)

    try:
        resp = await client.get(f"/api/v1/analysis/{_UUID_DONE}")
        assert resp.status_code == 200
        data = resp.json()
        assert "symbol" in data
        assert data["symbol"] == "EURUSD"
    finally:
        await _analysis_results.invalidate(_UUID_DONE)


async def test_get_analysis_db_fallback(client):
    """When report is not in cache but exists in DB, get_analysis returns it."""
    from app.core.models import AnalysisStatus

    report = AnalysisReport(symbol="GBPUSD", timeframe=Timeframe.H4)
    analysis_tasks[_UUID_DB] = AnalysisStatus(
        id=_UUID_DB,
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
        resp = await client.get(f"/api/v1/analysis/{_UUID_DB}")

    assert resp.status_code == 200
    data = resp.json()
    assert "symbol" in data
    assert data["symbol"] == "GBPUSD"


async def test_get_analysis_db_fallback_graceful_on_missing_table(client):
    """DB fallback doesn't raise when the table is missing — returns AnalysisStatus."""
    from app.core.models import AnalysisStatus

    analysis_tasks[_UUID_NO_TABLE] = AnalysisStatus(
        id=_UUID_NO_TABLE,
        status=AnalysisStatusType.COMPLETED,
        progress_pct=100.0,
    )

    with patch("app.api.v1.analysis.get_session_factory", side_effect=Exception("no such table")):
        resp = await client.get(f"/api/v1/analysis/{_UUID_NO_TABLE}")

    assert resp.status_code == 200


async def test_get_analysis_invalid_uuid(client):
    """GET /analysis/{id} with invalid UUID format returns 400."""
    resp = await client.get("/api/v1/analysis/not-a-uuid")
    assert resp.status_code == 400
    assert "Invalid analysis ID format" in resp.json()["detail"]


async def test_get_analysis_status_invalid_uuid(client):
    """GET /analysis/{id}/status with invalid UUID format returns 400."""
    resp = await client.get("/api/v1/analysis/not-a-uuid/status")
    assert resp.status_code == 400
    assert "Invalid analysis ID format" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# WebSocket rate limiting unit tests
# ---------------------------------------------------------------------------


def test_ws_connections_per_ip_cleanup_logic():
    """Test that _ws_connections_per_ip cleanup logic works correctly."""
    import time

    from app.api.v1.analysis import _WS_RATE_WINDOW, _ws_connections_per_ip

    _ws_connections_per_ip.clear()

    # Simulate connections with timestamps
    now = time.monotonic()
    _ws_connections_per_ip["192.168.1.1"] = [now - 30, now - 10, now - 5]  # All within window

    # Simulate cleanup (pruning expired entries)
    _ws_connections_per_ip["192.168.1.1"] = [
        t for t in _ws_connections_per_ip["192.168.1.1"] if now - t < _WS_RATE_WINDOW
    ]

    assert len(_ws_connections_per_ip["192.168.1.1"]) == 3

    # Simulate expired entries - after pruning, list becomes empty and should be deleted
    _ws_connections_per_ip["192.168.1.1"] = [now - 100, now - 70]  # Outside window
    _ws_connections_per_ip["192.168.1.1"] = [
        t for t in _ws_connections_per_ip["192.168.1.1"] if now - t < _WS_RATE_WINDOW
    ]

    # After pruning, if empty, the key should be removed
    if not _ws_connections_per_ip["192.168.1.1"]:
        del _ws_connections_per_ip["192.168.1.1"]

    assert "192.168.1.1" not in _ws_connections_per_ip

    _ws_connections_per_ip.clear()


def test_ws_connection_limit_constant():
    """Verify WebSocket connection limit is configured."""
    from app.api.v1.analysis import _WS_MAX_CONNECTIONS_PER_IP

    assert _WS_MAX_CONNECTIONS_PER_IP == 5


async def test_run_pipeline_sets_failed_status_on_exception(client):
    """_run_pipeline should set analysis_tasks status to FAILED when pipeline raises."""
    from app.api.v1.analysis import _background_tasks, _run_pipeline
    from app.core.models import AnalysisStatus, AnalysisStatusType
    from app.modules.pipeline import analysis_tasks

    analysis_tasks.clear()
    _background_tasks.clear()

    # Create a mock pipeline that raises an exception
    mock_pipeline = MagicMock()
    mock_pipeline.analysis_id = _UUID_TEST
    mock_pipeline.run = AsyncMock(side_effect=Exception("Test pipeline failure"))

    # Mock pipeline.fail() to set status in analysis_tasks (like real pipeline does)
    def _set_failed(error):
        analysis_tasks[_UUID_TEST] = AnalysisStatus(
            id=_UUID_TEST,
            status=AnalysisStatusType.FAILED,
            error_message=error,
        )

    mock_pipeline.fail = MagicMock(side_effect=_set_failed)

    # Run the pipeline directly (bypassing trigger_analysis)
    await _run_pipeline(mock_pipeline)

    # Verify status was set to FAILED
    status = analysis_tasks.get(_UUID_TEST)
    assert status is not None
    assert status.status == AnalysisStatusType.FAILED
    assert "Test pipeline failure" in (status.error_message or "")

    # Cleanup
    _background_tasks.clear()
    analysis_tasks.clear()


async def test_run_pipeline_sets_failed_status_on_none_report(client):
    """_run_pipeline should set analysis_tasks status to FAILED when pipeline returns None."""
    from app.api.v1.analysis import _background_tasks, _run_pipeline
    from app.core.models import AnalysisStatus, AnalysisStatusType
    from app.modules.pipeline import analysis_tasks

    analysis_tasks.clear()
    _background_tasks.clear()

    # Create a mock pipeline that returns None
    mock_pipeline = MagicMock()
    mock_pipeline.analysis_id = _UUID_TEST
    mock_pipeline.run = AsyncMock(return_value=None)

    # Mock pipeline.fail() to set status in analysis_tasks (like real pipeline does)
    def _set_failed(error):
        analysis_tasks[_UUID_TEST] = AnalysisStatus(
            id=_UUID_TEST,
            status=AnalysisStatusType.FAILED,
            error_message=error,
        )

    mock_pipeline.fail = MagicMock(side_effect=_set_failed)

    # Run the pipeline directly
    await _run_pipeline(mock_pipeline)

    # Verify status was set to FAILED
    status = analysis_tasks.get(_UUID_TEST)
    assert status is not None
    assert status.status == AnalysisStatusType.FAILED

    # Cleanup
    _background_tasks.clear()
    analysis_tasks.clear()
