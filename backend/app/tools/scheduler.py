"""
Scheduler Tool: schedule_check and cancel_checks.
Manages timed SLA checks and dead-man switches in the timers table.
Runs an async background check loop and responds to POST /api/tick for external cron calls.
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.core.orchestrator_bridge as orchestrator
from backend.app.core.clock import now as clock_now
from backend.app.db.models import TimerModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.tools.registry import tools


@tools.register("schedule_check")
async def schedule_check(
    case_id: str,
    run_at: datetime,
    reason: str,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Schedule a future verification check for a case."""
    timer_id = f"tmr-{uuid.uuid4().hex[:8]}"

    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        timer = TimerModel(
            id=timer_id,
            case_id=case_id,
            run_at=run_at,
            reason=reason,
            status="pending",
            created_at=clock_now(),
        )
        session.add(timer)
        await session.commit()
        return {
            "id": timer.id,
            "case_id": timer.case_id,
            "run_at": timer.run_at.isoformat(),
            "reason": timer.reason,
            "status": timer.status,
        }

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)


@tools.register("cancel_checks")
async def cancel_checks(
    case_id: str,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Cancel all pending checks for a case."""
    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        stmt = (
            update(TimerModel)
            .where(TimerModel.case_id == case_id)
            .where(TimerModel.status == "pending")
            .values(status="cancelled")
        )
        res = await session.execute(stmt)
        await session.commit()
        return {"case_id": case_id, "cancelled_count": res.rowcount}

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)


async def process_due_timers(db: Optional[AsyncSession] = None) -> List[Dict[str, Any]]:
    """
    Find all pending timers whose run_at <= clock.now(), mark them fired,
    and invoke orchestrator.resume_case.
    """
    now = clock_now()
    fired_timers: List[Dict[str, Any]] = []

    async def _process(session: AsyncSession) -> List[Dict[str, Any]]:
        stmt = (
            select(TimerModel)
            .where(TimerModel.status == "pending")
            .where(TimerModel.run_at <= now)
        )
        res = await session.execute(stmt)
        due_timers = res.scalars().all()

        for timer in due_timers:
            timer.status = "fired"
            session.add(timer)
            fired_timers.append({
                "id": timer.id,
                "case_id": timer.case_id,
                "reason": timer.reason,
                "run_at": timer.run_at.isoformat(),
            })

        await session.commit()

        # Notify orchestrator for each fired timer
        for item in fired_timers:
            try:
                await orchestrator.resume_case(
                    case_id=item["case_id"],
                    reason=item["reason"],
                    payload={"timer_id": item["id"], "fired_at": now.isoformat()},
                    db=session,
                )
            except Exception as e:
                print(f"[scheduler warning] Error resuming case {item['case_id']}: {e}")

        return fired_timers

    if db is not None:
        return await _process(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _process(session)


class SchedulerBackgroundWorker:
    """Background task polling for due timers every interval seconds."""
    def __init__(self, interval_seconds: float = 5.0) -> None:
        self.interval = interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while self._running:
            try:
                await process_due_timers()
            except Exception as e:
                print(f"[scheduler error] Background timer loop error: {e}")
            await asyncio.sleep(self.interval)


scheduler_worker = SchedulerBackgroundWorker()
