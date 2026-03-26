"""REST API + WebSocket endpoints for triggering and monitoring analysis."""

import asyncio
import logging

from cachetools import TTLCache
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.api.v1.validators import validate_symbol
from app.core.models import AnalysisReport, AnalysisStatus, AnalysisStatusType, Timeframe
from app.core.rate_limit import limiter
from app.modules.pipeline import AnalysisPipeline, analysis_tasks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

# Limit concurrent pipeline executions to avoid exhausting external API rate limits
_MAX_CONCURRENT_ANALYSES = 5
_analysis_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_ANALYSES)


class AnalysisRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1


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

    pipeline = AnalysisPipeline(symbol=body.symbol, timeframe=body.timeframe)

    # Run pipeline as a background coroutine — store ref to prevent GC
    _background_tasks[pipeline.analysis_id] = asyncio.create_task(_run_pipeline(pipeline))

    return AnalysisResponse(analysis_id=pipeline.analysis_id, status="pending")


# Store completed reports and background task refs (TTL=1h, bounded)
_analysis_results: TTLCache[str, AnalysisReport] = TTLCache(maxsize=1000, ttl=3600)
_background_tasks: TTLCache[str, asyncio.Task[None]] = TTLCache(maxsize=1000, ttl=3600)


async def _run_pipeline(pipeline: AnalysisPipeline) -> None:
    """Execute pipeline and store result."""
    async with _analysis_semaphore:
        report = await pipeline.run()
        if report is not None:
            _analysis_results[pipeline.analysis_id] = report


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str) -> AnalysisReport | AnalysisStatus:
    """Get analysis result or current status.

    Returns AnalysisReport when completed, AnalysisStatus otherwise.
    """
    status: AnalysisStatus | None = analysis_tasks.get(analysis_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if status.status == AnalysisStatusType.COMPLETED:
        report: AnalysisReport | None = _analysis_results.get(analysis_id)
        if report is not None:
            return report
        # Report was persisted but not in memory — return status
        return status

    return status


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str) -> AnalysisStatus:
    """Get current analysis status (progress, steps)."""
    status: AnalysisStatus | None = analysis_tasks.get(analysis_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return status


@router.websocket("/ws/analysis/{analysis_id}")
async def analysis_websocket(websocket: WebSocket, analysis_id: str) -> None:
    """WebSocket endpoint pushing AnalysisStatus updates until completion."""
    await websocket.accept()

    try:
        last_sent: str = ""
        while True:
            status = analysis_tasks.get(analysis_id)
            if status is None:
                await websocket.send_json({"error": "Analysis not found"})
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
