"""REST API + WebSocket endpoints for triggering and monitoring analysis."""

import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.api.v1.validators import validate_analysis_id, validate_symbol
from app.core.config import get_settings
from app.core.database import AnalysisResult, get_session_factory
from app.core.models import AnalysisReport, AnalysisStatus, AnalysisStatusType, IndicatorPreset, Timeframe
from app.core.rate_limit import limiter
from app.modules.data_acquisition.redis_cache import create_redis_cache
from app.modules.pipeline import AnalysisPipeline, analysis_tasks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

_ANALYSIS_NOT_FOUND = "Analysis not found"

# Limit concurrent pipeline executions to avoid exhausting external API rate limits
_MAX_CONCURRENT_ANALYSES = 5
_MAX_BACKGROUND_TASKS = 100  # Prevent unbounded memory growth
_analysis_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_ANALYSES)
# Lock for atomic guard against duplicate analysis_id
_analysis_guard_lock = asyncio.Lock()

# WebSocket per-IP connection limiter: max 5 concurrent connections per IP, tracked for 60s
_WS_MAX_CONNECTIONS_PER_IP = 5
_WS_RATE_WINDOW = 60
_ws_connections_per_ip: dict[str, dict[str, float]] = {}


class AnalysisRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1
    preset: IndicatorPreset = IndicatorPreset.INVESTING


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str


@router.post("/analysis", response_model=AnalysisResponse)
@limiter.limit("10/minute")
async def trigger_analysis(request: Request, body: AnalysisRequest) -> AnalysisResponse:
    """Trigger a full analysis pipeline for a given symbol and timeframe.

    Returns an analysis_id to poll for status/results.
    """
    validate_symbol(body.symbol)

    pipeline = AnalysisPipeline(symbol=body.symbol, timeframe=body.timeframe, preset=body.preset)

    # Guard against duplicate analysis_id (race condition protection with lock)
    async with _analysis_guard_lock:
        if pipeline.analysis_id in _background_tasks:
            raise HTTPException(status_code=409, detail="Analysis already running for this ID")
        # Prevent unbounded memory growth
        if len(_background_tasks) >= _MAX_BACKGROUND_TASKS:
            raise HTTPException(status_code=503, detail="Too many concurrent analyses")
        # Run pipeline as a background coroutine — store ref to prevent GC
        _background_tasks[pipeline.analysis_id] = asyncio.create_task(_run_pipeline(pipeline))

    return AnalysisResponse(analysis_id=pipeline.analysis_id, status="pending")


# Store completed reports in Redis (TTL=1h), background task refs in memory (runtime objects)
_analysis_results = create_redis_cache(default_ttl=3600, key_prefix="analysis:result")
# Use plain dict instead of TTLCache — active tasks must never be evicted by size limit.
# Tasks are removed in _run_pipeline's finally block when they complete.
_background_tasks: dict[str, asyncio.Task[None]] = {}


async def _run_pipeline(pipeline: AnalysisPipeline) -> None:
    """Execute pipeline: cache report first, then publish COMPLETED."""
    async with _analysis_semaphore:
        try:
            report = await pipeline.run()
            if report is not None:
                try:
                    await _analysis_results.set(pipeline.analysis_id, report.model_dump(mode="json"))
                except Exception:
                    logger.error("Failed to cache analysis result for %s", pipeline.analysis_id, exc_info=True)
                pipeline.complete()
            else:
                pipeline.fail("Pipeline returned no report")
        except Exception as exc:
            logger.exception("Pipeline failed for analysis %s", pipeline.analysis_id)
            pipeline.fail(str(exc))
        finally:
            _background_tasks.pop(pipeline.analysis_id, None)


async def _load_report_from_db(analysis_id: str) -> AnalysisReport | None:
    """Try to load a persisted report from the database (defense-in-depth)."""
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            row = await session.get(AnalysisResult, analysis_id)
            if row is not None and row.result_json:
                return AnalysisReport.model_validate_json(row.result_json)
    except Exception:
        logger.debug("DB fallback failed for analysis %s", analysis_id, exc_info=True)
    return None


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str) -> AnalysisReport | AnalysisStatus:
    """Get analysis result or current status.

    Returns AnalysisReport when completed, AnalysisStatus otherwise.
    """
    validate_analysis_id(analysis_id)
    status: AnalysisStatus | None = analysis_tasks.get(analysis_id)
    if status is None:
        raise HTTPException(status_code=404, detail=_ANALYSIS_NOT_FOUND)

    if status.status == AnalysisStatusType.COMPLETED:
        cached = await _analysis_results.get(analysis_id)
        if cached is not None:
            try:
                return AnalysisReport.model_validate(cached)
            except Exception:
                logger.warning(
                    "Cached analysis result for %s failed validation, invalidating cache", analysis_id, exc_info=True
                )
                await _analysis_results.invalidate(analysis_id)
        # Cache miss — try DB fallback (defense-in-depth)
        report = await _load_report_from_db(analysis_id)
        if report is not None:
            await _analysis_results.set(analysis_id, report.model_dump(mode="json"))
            return report
        return status

    return status


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str) -> AnalysisStatus:
    """Get current analysis status (progress, steps)."""
    validate_analysis_id(analysis_id)
    status: AnalysisStatus | None = analysis_tasks.get(analysis_id)
    if status is None:
        raise HTTPException(status_code=404, detail=_ANALYSIS_NOT_FOUND)
    return status


@router.websocket("/ws/analysis/{analysis_id}")
async def analysis_websocket(websocket: WebSocket, analysis_id: str) -> None:
    """WebSocket endpoint pushing AnalysisStatus updates until completion."""
    validate_analysis_id(analysis_id)
    # Origin check for WebSocket security
    origin = websocket.headers.get("origin", "")
    settings = get_settings()
    allowed_origins = settings.CORS_ORIGINS
    if origin and origin not in allowed_origins:
        logger.warning("WebSocket rejected: origin %s not in allowed origins", origin)
        await websocket.close(code=1008)
        return
    # Per-IP rate limiting for WebSocket connections
    client_ip = websocket.client.host if websocket.client else "unknown"
    conn_id = str(uuid.uuid4())
    now = time.monotonic()
    connections = _ws_connections_per_ip.get(client_ip, {})
    # Prune expired entries
    connections = {cid: ts for cid, ts in connections.items() if now - ts < _WS_RATE_WINDOW}
    if len(connections) >= _WS_MAX_CONNECTIONS_PER_IP:
        logger.warning("WebSocket rate limited: IP %s has %d connections", client_ip, len(connections))
        await websocket.close(code=1008)
        return
    connections[conn_id] = now
    _ws_connections_per_ip[client_ip] = connections
    await websocket.accept()

    try:
        last_sent: str = ""
        while True:
            status = analysis_tasks.get(analysis_id)
            if status is None:
                await websocket.send_json({"error": _ANALYSIS_NOT_FOUND})
                break

            status_json = status.model_dump_json()
            if status_json != last_sent:
                await websocket.send_text(status_json)
                last_sent = status_json

            if status.status in (AnalysisStatusType.COMPLETED, AnalysisStatusType.FAILED):
                break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected for analysis %s", analysis_id)
    finally:
        # Cleanup: remove this specific connection from per-IP tracking
        if client_ip in _ws_connections_per_ip:
            _ws_connections_per_ip[client_ip].pop(conn_id, None)
            if not _ws_connections_per_ip[client_ip]:
                del _ws_connections_per_ip[client_ip]
