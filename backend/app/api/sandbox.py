"""
Department Sandbox API Router for CivicPilot.
Provides demo control endpoints simulating department dispatcher rejections,
field crew check-ins, crew no-shows, and repair photo uploads.
Source of truth: docs/CONTRACT.md Section 7.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.sandbox.service import sandbox_service
from backend.app.schemas import (
    SandboxCrewCheckinRequest,
    SandboxCrewNoShowRequest,
    SandboxRejectRequest,
    SandboxRepairPhotoRequest,
)

router = APIRouter(prefix="/sandbox", tags=["Department Sandbox"])


@router.post("/tickets/{id}/reject")
async def reject_ticket(
    id: str,
    req: SandboxRejectRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Demo control: simulate department rejecting the work ticket."""
    return await sandbox_service.reject_ticket(ticket_id=id, reason=req.reason, db=db)


@router.post("/tickets/{id}/crew-checkin")
async def crew_checkin(
    id: str,
    req: SandboxCrewCheckinRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Demo control: simulate field crew arriving and checking in at the site."""
    return await sandbox_service.crew_checkin(
        ticket_id=id,
        lat=req.lat,
        lng=req.lng,
        notes=req.notes,
        db=db,
    )


@router.post("/tickets/{id}/crew-no-show")
async def crew_no_show(
    id: str,
    req: SandboxCrewNoShowRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Demo control: simulate assigned crew failing to appear on site."""
    return await sandbox_service.crew_no_show(ticket_id=id, reason=req.reason, db=db)


@router.post("/tickets/{id}/repair-photo")
async def upload_repair_photo(
    id: str,
    req: SandboxRepairPhotoRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Demo control: simulate crew completing repairs and uploading photo proof."""
    return await sandbox_service.upload_repair_photo(
        ticket_id=id,
        photo_url=req.photo_url,
        notes=req.notes,
        db=db,
    )
