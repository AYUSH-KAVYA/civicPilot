"""
Health, Cron Tick & System API Router for CivicPilot.
GET /api/health
POST /api/tick
GET /api/events/stream
GET /api/uploads/{filename}
Source of truth: docs/CONTRACT.md Section 7.
"""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import now as clock_now
from backend.app.core.config import get_settings
from backend.app.core.events import sse_event_stream
from backend.app.db.session import get_db
from backend.app.tools.scheduler import process_due_timers

router = APIRouter(tags=["Health & System"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for Render, UptimeRobot, and monitoring services."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "civicpilot-api",
        "timestamp": clock_now().isoformat(),
        "sim_time_scale": settings.SIM_TIME_SCALE,
        "mock_llm": settings.MOCK_LLM,
    }


@router.post("/tick")
async def tick(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Called by external cron (e.g. cron-job.org / UptimeRobot every 5 minutes).
    Evaluates and processes all due scheduled checks/timers in the database.
    """
    fired = await process_due_timers(db=db)
    return {
        "status": "success",
        "processed_count": len(fired),
        "fired_timers": fired,
        "timestamp": clock_now().isoformat(),
    }


@router.get("/events/stream")
async def global_event_stream() -> StreamingResponse:
    """Global SSE stream of all municipal audit events for officer dashboards."""
    return StreamingResponse(
        sse_event_stream(case_id=None),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/uploads/{filename}")
async def get_uploaded_file(filename: str) -> FileResponse:
    """Serve local disk fallback media uploads."""
    settings = get_settings()
    file_path = Path(settings.UPLOAD_DIR) / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(file_path)
