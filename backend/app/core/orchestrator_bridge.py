"""
Orchestrator Bridge.
Imports the real P3 orchestrator if available, or seamlessly delegates
to orchestrator_stub until P3's code is merged.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

try:
    from backend.app.orchestrator import (
        handle_approval as _real_handle_approval,
    )
    from backend.app.orchestrator import (
        handle_citizen_confirmation as _real_handle_citizen_confirmation,
    )
    from backend.app.orchestrator import (
        handle_citizen_message as _real_handle_citizen_message,
    )
    from backend.app.orchestrator import (
        handle_sandbox_signal as _real_handle_sandbox_signal,
    )
    from backend.app.orchestrator import (
        resume_case as _real_resume_case,
    )
    from backend.app.orchestrator import (  # type: ignore
        start_case as _real_start_case,
    )
    _USE_REAL = True
except (ImportError, AttributeError):
    _USE_REAL = False

import backend.app.orchestrator_stub as stub


async def start_case(case_id: str, db: Optional[AsyncSession] = None) -> None:
    if _USE_REAL:
        await _real_start_case(case_id, db=db)
    else:
        await stub.start_case(case_id, db=db)


async def resume_case(
    case_id: str,
    reason: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    if _USE_REAL:
        await _real_resume_case(case_id, reason, payload=payload, db=db)
    else:
        await stub.resume_case(case_id, reason, payload=payload, db=db)


async def handle_citizen_message(
    case_id: str,
    text: str,
    image_urls: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    if _USE_REAL:
        await _real_handle_citizen_message(case_id, text, image_urls=image_urls, db=db)
    else:
        await stub.handle_citizen_message(case_id, text, image_urls=image_urls, db=db)


async def handle_citizen_confirmation(
    case_id: str,
    confirmed: bool,
    comment: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    if _USE_REAL:
        await _real_handle_citizen_confirmation(case_id, confirmed, comment=comment, db=db)
    else:
        await stub.handle_citizen_confirmation(case_id, confirmed, comment=comment, db=db)


async def handle_approval(
    approval_id: str,
    decision: str,
    officer: str,
    note: Optional[str] = None,
    db: Optional[AsyncSession] = None,
) -> None:
    if _USE_REAL:
        await _real_handle_approval(approval_id, decision, officer, note=note, db=db)
    else:
        await stub.handle_approval(approval_id, decision, officer, note=note, db=db)


async def handle_sandbox_signal(
    case_id: str,
    signal: Dict[str, Any],
    db: Optional[AsyncSession] = None,
) -> None:
    if _USE_REAL:
        await _real_handle_sandbox_signal(case_id, signal, db=db)
    else:
        await stub.handle_sandbox_signal(case_id, signal, db=db)
