"""
Audit Events & Live Event Stream (SSE) for CivicPilot.
Handles event emission, PII masking, persistence in DB, and real-time SSE broadcasting.
Source of truth: docs/CONTRACT.md Section 5.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import now as clock_now
from backend.app.db.models import CaseEventModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.schemas import AgentName, CaseEvent, Phase

# ---------------------------------------------------------------------------
# PII Masking Utilities
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")


def mask_contact(raw_contact: str) -> str:
    """Mask a phone number or email address for citizen privacy."""
    contact = raw_contact.strip()
    if "@" in contact:
        parts = contact.split("@", 1)
        name, domain = parts[0], parts[1]
        if len(name) <= 2:
            masked_name = name[0] + "***"
        else:
            masked_name = name[0] + "***" + name[-1]
        return f"{masked_name}@{domain}"

    # Phone number masking
    digits = re.sub(r"\D", "", contact)
    if len(digits) >= 4:
        return f"***-***-{digits[-4:]}"
    return "***-***-****"


def mask_pii_string(text: str) -> str:
    """Mask emails and phone numbers inside free-form text."""
    if not text:
        return text
    text = EMAIL_REGEX.sub("[EMAIL_MASKED]", text)
    text = PHONE_REGEX.sub("[PHONE_MASKED]", text)
    return text


def mask_pii_data(data: Any) -> Any:
    """Recursively mask PII inside dicts, lists, and strings, and convert datetimes to ISO strings."""
    if isinstance(data, (datetime, )):
        return data.isoformat()
    elif isinstance(data, str):
        return mask_pii_string(data)
    elif isinstance(data, dict):
        return {k: mask_pii_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_pii_data(item) for item in data]
    return data


# ---------------------------------------------------------------------------
# In-Memory Event Broadcaster for SSE
# ---------------------------------------------------------------------------

class EventBroadcaster:
    def __init__(self) -> None:
        self._case_subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._global_subscribers: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()

    async def subscribe_case(self, case_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        async with self._lock:
            if case_id not in self._case_subscribers:
                self._case_subscribers[case_id] = set()
            self._case_subscribers[case_id].add(queue)
        return queue

    async def unsubscribe_case(self, case_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            if case_id in self._case_subscribers:
                self._case_subscribers[case_id].discard(queue)
                if not self._case_subscribers[case_id]:
                    del self._case_subscribers[case_id]

    async def subscribe_global(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._global_subscribers.add(queue)
        return queue

    async def unsubscribe_global(self, queue: asyncio.Queue) -> None:
        async with self._lock:
            self._global_subscribers.discard(queue)

    async def broadcast(self, event: CaseEvent) -> None:
        """Deliver event to all per-case and global subscribers."""
        async with self._lock:
            queues_to_notify: List[asyncio.Queue] = []
            if event.case_id in self._case_subscribers:
                queues_to_notify.extend(self._case_subscribers[event.case_id])
            queues_to_notify.extend(self._global_subscribers)

        for q in queues_to_notify:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Drop oldest item if full to prevent blocking
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass


broadcaster = EventBroadcaster()


# ---------------------------------------------------------------------------
# Event Emission Helper (CONTRACT.md Section 5)
# ---------------------------------------------------------------------------

async def emit_event(
    case_id: str,
    agent: AgentName | str,
    phase: Phase | str,
    summary: str,
    detail: Optional[Dict[str, Any]] = None,
    tool_name: Optional[str] = None,
    reason: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> CaseEvent:
    """
    Emit an audit event:
    1. Mask PII in summary and detail.
    2. Persist record to DB (case_events).
    3. Broadcast to active SSE streams (per-case and global).
    """
    # 1. PII Masking
    clean_summary = mask_pii_string(summary)
    clean_detail = mask_pii_data(detail) if detail is not None else None
    clean_reason = mask_pii_string(reason) if reason is not None else None

    agent_str = agent.value if isinstance(agent, AgentName) else str(agent)
    phase_str = phase.value if isinstance(phase, Phase) else str(phase)

    event_id = str(uuid.uuid4())
    event_ts = clock_now()

    # 2. Persist to DB
    event_model = CaseEventModel(
        id=event_id,
        case_id=case_id,
        ts=event_ts,
        agent=agent_str,
        phase=phase_str,
        summary=clean_summary,
        detail=clean_detail,
        tool_name=tool_name,
        reason=clean_reason,
    )

    if db is not None:
        db.add(event_model)
        await db.commit()
    else:
        async with AsyncSessionLocal() as session:
            session.add(event_model)
            await session.commit()

    # Create pydantic event
    event = CaseEvent(
        id=event_id,
        case_id=case_id,
        ts=event_ts,
        agent=AgentName(agent_str),
        phase=Phase(phase_str),
        summary=clean_summary,
        detail=clean_detail,
        tool_name=tool_name,
        reason=clean_reason,
    )

    # 3. Broadcast to SSE subscribers
    await broadcaster.broadcast(event)

    return event


# ---------------------------------------------------------------------------
# SSE Generator Helper
# ---------------------------------------------------------------------------

async def sse_event_stream(
    case_id: Optional[str] = None,
    heartbeat_interval: float = 15.0,
) -> AsyncGenerator[str, None]:
    """
    Yield Server-Sent Events formatted data for FastAPI StreamingResponse.
    If case_id is None, streams global officer events.
    """
    if case_id:
        queue = await broadcaster.subscribe_case(case_id)
    else:
        queue = await broadcaster.subscribe_global()

    try:
        while True:
            try:
                # Wait for next event with heartbeat timeout
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_interval)
                payload = json.dumps(event.model_dump(mode="json"))
                yield f"event: message\ndata: {payload}\n\n"
            except asyncio.TimeoutError:
                # Heartbeat comment to keep HTTP/SSE connection alive through proxies
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        if case_id:
            await broadcaster.unsubscribe_case(case_id, queue)
        else:
            await broadcaster.unsubscribe_global(queue)
