"""REST API + WebSocket endpoints for triggering and monitoring analysis."""

import asyncio
import logging
import re

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.models import AnalysisReport, AnalysisStatus, AnalysisStatusType, Timeframe
from app.modules.pipeline import AnalysisPipeline, analysis_tasks

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9/\-]{2,20}$")


class AnalysisRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str


@router.post("/analysis", response_model=AnalysisResponse)
async def trigger_analysis(body: AnalysisRequest) -> AnalysisResponse:
    """Trigger a full analysis pipeline for a given symbol and timeframe.

    Returns an analysis_id to poll for status/results.
    """
    if not SYMBOL_PATTERN.match(body.symbol):
        raise HTTPException(status_code=400, detail="Nieprawidlowy format symbolu")

    valid_timeframes = {t.value for t in Timeframe}
    if body.timeframe not in valid_timeframes:
        allowed = ", ".join(valid_timeframes)
        raise HTTPException(status_code=400, detail=f"Nieprawidlowy timeframe. Dozwolone: {allowed}")

    pipeline = AnalysisPipeline(symbol=body.symbol, timeframe=body.timeframe)

    # Run pipeline as a background coroutine — store ref to prevent GC
    _background_tasks[pipeline.analysis_id] = asyncio.create_task(_run_pipeline(pipeline))

    return AnalysisResponse(analysis_id=pipeline.analysis_id, status="pending")


# Store completed reports and background task refs
_analysis_results: dict[str, AnalysisReport] = {}
_background_tasks: dict[str, asyncio.Task] = {}


async def _run_pipeline(pipeline: AnalysisPipeline) -> None:
    """Execute pipeline and store result."""
    report = await pipeline.run()
    if report is not None:
        _analysis_results[pipeline.analysis_id] = report


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str) -> AnalysisReport | AnalysisStatus:
    """Get analysis result or current status.

    Returns AnalysisReport when completed, AnalysisStatus otherwise.
    """
    status = analysis_tasks.get(analysis_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Analiza nie znaleziona")

    if status.status == AnalysisStatusType.COMPLETED:
        report = _analysis_results.get(analysis_id)
        if report is not None:
            return report
        # Report was persisted but not in memory — return status
        return status

    return status


@router.get("/analysis/{analysis_id}/status", response_model=AnalysisStatus)
async def get_analysis_status(analysis_id: str) -> AnalysisStatus:
    """Get current analysis status (progress, steps)."""
    status = analysis_tasks.get(analysis_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Analiza nie znaleziona")
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
                await websocket.send_json({"error": "Analiza nie znaleziona"})
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
