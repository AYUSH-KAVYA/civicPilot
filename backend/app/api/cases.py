"""
Cases API Router for CivicPilot.
Handles case submission, officer listing/filters, detail retrieval, audit events,
live SSE streaming, citizen follow-up messages, confirmation, and officer resolution.
Source of truth: docs/CONTRACT.md Section 7.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.core.orchestrator_bridge as orchestrator
from backend.app.core.auth import (
    create_case_access_token,
    get_current_officer,
    require_case_or_officer_access,
)
from backend.app.core.clock import now as clock_now
from backend.app.core.events import (
    emit_event,
    mask_contact,
    sse_event_stream,
)
from backend.app.core.storage import upload_image_bytes
from backend.app.db.models import CaseEventModel, CaseModel, CitizenModel
from backend.app.db.session import get_db
from backend.app.schemas import (
    AgentName,
    CaseCreateResponse,
    CaseEvent,
    CaseState,
    CaseStatus,
    Channel,
    CitizenConfirmRequest,
    OfficerResolveRequest,
    Phase,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    # Multipart form fields
    text: Optional[str] = Form(None),
    contact: Optional[str] = Form(None),
    language: str = Form("en"),
    channel: str = Form("web"),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    address_text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
) -> CaseCreateResponse:
    """
    File a new citizen grievance. Accepts multipart/form-data or application/json.
    Returns case_id and a case-scoped access_token for the citizen.
    """
    image_urls: List[str] = []

    # Check if request is JSON
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        text = body.get("text", "")
        contact = body.get("contact", "")
        language = body.get("language", "en")
        channel = body.get("channel", "web")
        lat = body.get("lat")
        lng = body.get("lng")
        address_text = body.get("address_text")
        image_urls = body.get("image_urls", [])

    if not text or not contact:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required fields: 'text' and 'contact' are mandatory.",
        )

    # Handle image upload if provided via multipart
    if image and image.filename:
        file_bytes = await image.read()
        if len(file_bytes) > 0:
            uploaded_url = await upload_image_bytes(
                file_bytes=file_bytes,
                original_filename=image.filename,
                content_type=image.content_type or "image/jpeg",
            )
            image_urls.append(uploaded_url)

    case_id = f"case-{uuid.uuid4().hex[:8]}"
    created_at = clock_now()
    masked_contact = mask_contact(contact)

    # Validate channel enum
    try:
        channel_enum = Channel(channel)
    except ValueError:
        channel_enum = Channel.web

    # Initial CaseState
    state_dict: Dict[str, Any] = {
        "id": case_id,
        "created_at": created_at.isoformat(),
        "updated_at": created_at.isoformat(),
        "status": CaseStatus.NEW.value,
        "deadline_at": None,
        "citizen": {
            "contact_masked": masked_contact,
            "language": language,
        },
        "raw": {
            "text": text,
            "image_urls": image_urls,
            "lat": lat,
            "lng": lng,
            "address_text": address_text,
            "channel": channel_enum.value,
        },
        "intake": None,
        "triage": None,
        "plan": None,
        "tickets": [],
        "flags": {
            "needs_human": False,
            "human_reason": None,
            "reopen_count": 0,
            "merged_into": None,
            "duplicate_of": [],
        },
    }

    # Persist case
    case_model = CaseModel(
        id=case_id,
        created_at=created_at,
        updated_at=created_at,
        status=CaseStatus.NEW.value,
        state=state_dict,
    )
    db.add(case_model)

    # Persist citizen raw contact separately
    citizen_model = CitizenModel(
        id=f"cit-{uuid.uuid4().hex[:8]}",
        case_id=case_id,
        raw_contact=contact,
        masked_contact=masked_contact,
        language=language,
        created_at=created_at,
    )
    db.add(citizen_model)
    await db.commit()

    # Generate case-scoped citizen access token
    access_token = create_case_access_token(case_id)

    # Launch orchestrator in background to execute intake -> triage -> plan -> action
    background_tasks.add_task(orchestrator.start_case, case_id)

    return CaseCreateResponse(case_id=case_id, access_token=access_token)


@router.get("", response_model=List[CaseState])
async def list_cases(
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    officer: Dict[str, Any] = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
) -> List[CaseState]:
    """List all cases with optional filtering. Requires officer JWT."""
    stmt = select(CaseModel).order_by(CaseModel.created_at.desc())
    if status:
        stmt = stmt.where(CaseModel.status == status)
    if department:
        stmt = stmt.where(CaseModel.department_id == department)
    if urgency:
        stmt = stmt.where(CaseModel.urgency == urgency)

    result = await db.execute(stmt)
    cases = result.scalars().all()
    return [CaseState.model_validate(c.state) for c in cases]


@router.get("/{id}", response_model=CaseState)
async def get_case(
    id: str,
    auth: Dict[str, Any] = Depends(require_case_or_officer_access),
    db: AsyncSession = Depends(get_db),
) -> CaseState:
    """Retrieve full CaseState for a case. Requires officer JWT or matching case token."""
    case = await db.get(CaseModel, id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {id} not found")
    return CaseState.model_validate(case.state)


@router.get("/{id}/events", response_model=List[CaseEvent])
async def get_case_events(
    id: str,
    auth: Dict[str, Any] = Depends(require_case_or_officer_access),
    db: AsyncSession = Depends(get_db),
) -> List[CaseEvent]:
    """Retrieve the complete audit event trail for a case."""
    stmt = (
        select(CaseEventModel)
        .where(CaseEventModel.case_id == id)
        .order_by(CaseEventModel.ts.asc())
    )
    res = await db.execute(stmt)
    events = res.scalars().all()
    return [CaseEvent.model_validate(e) for e in events]


@router.get("/{id}/stream")
async def stream_case_events(
    id: str,
    authorization: Optional[str] = Header(None),
    x_case_token: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE live event stream for this specific case."""
    case = await db.get(CaseModel, id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {id} not found")

    return StreamingResponse(
        sse_event_stream(case_id=id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{id}/messages")
async def citizen_message(
    id: str,
    request: Request,
    auth: Dict[str, Any] = Depends(require_case_or_officer_access),
    db: AsyncSession = Depends(get_db),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """Citizen provides additional information, photos, or feedback."""
    image_urls: List[str] = []

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        text = body.get("text", "")
        image_urls = body.get("image_urls", [])

    if image and image.filename:
        file_bytes = await image.read()
        if len(file_bytes) > 0:
            url = await upload_image_bytes(file_bytes, image.filename, image.content_type or "image/jpeg")
            image_urls.append(url)

    if not text and not image_urls:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message must contain text or image.")

    await orchestrator.handle_citizen_message(case_id=id, text=text or "", image_urls=image_urls, db=db)
    return {"status": "received", "case_id": id}


@router.post("/{id}/confirm")
async def citizen_confirm(
    id: str,
    req: CitizenConfirmRequest,
    auth: Dict[str, Any] = Depends(require_case_or_officer_access),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Citizen confirms or rejects repair closure."""
    await orchestrator.handle_citizen_confirmation(
        case_id=id,
        confirmed=req.confirmed,
        comment=req.comment,
        db=db,
    )
    return {"status": "processed", "confirmed": req.confirmed}


@router.post("/{id}/resolve")
async def officer_resolve(
    id: str,
    req: OfficerResolveRequest,
    officer: Dict[str, Any] = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Officer resolves a case flagged as NEEDS_HUMAN."""
    case = await db.get(CaseModel, id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {id} not found")

    officer_sub = officer.get("sub", "officer-admin")
    case.status = CaseStatus.CLOSED.value
    state = dict(case.state)
    state["status"] = CaseStatus.CLOSED.value
    flags = state.setdefault("flags", {})
    flags["needs_human"] = False
    flags["human_reason"] = f"Resolved manually by {officer_sub}: {req.note}"
    case.state = state
    db.add(case)
    await db.commit()

    await emit_event(
        case_id=id,
        agent=AgentName.officer,
        phase=Phase.guardrail,
        summary=f"Case resolved manually by officer {officer_sub}: {req.note}",
        detail={"officer": officer_sub, "note": req.note},
        db=db,
    )

    return {"status": "resolved", "case_id": id, "note": req.note}
