"""
Approvals API Router for CivicPilot.
Handles listing and deciding supervisor approvals for sensitive/critical actions.
Source of truth: docs/CONTRACT.md Section 7.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.core.orchestrator_bridge as orchestrator
from backend.app.core.auth import get_current_officer
from backend.app.db.models import ApprovalModel
from backend.app.db.session import get_db
from backend.app.schemas import Approval, ApprovalDecisionRequest

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("", response_model=List[Approval])
async def list_approvals(
    status: str = Query("pending"),
    officer: Dict[str, Any] = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
) -> List[Approval]:
    """List approval requests. Filterable by status (default: pending). Requires officer JWT."""
    stmt = (
        select(ApprovalModel)
        .where(ApprovalModel.status == status)
        .order_by(ApprovalModel.requested_at.asc())
    )
    result = await db.execute(stmt)
    approvals = result.scalars().all()
    return [Approval.model_validate(a) for a in approvals]


@router.post("/{id}")
async def decide_approval(
    id: str,
    req: ApprovalDecisionRequest,
    officer: Dict[str, Any] = Depends(get_current_officer),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Approve or reject a pending action step. Requires officer JWT."""
    officer_sub = officer.get("sub", "officer-admin")
    await orchestrator.handle_approval(
        approval_id=id,
        decision=req.decision.value,
        officer=officer_sub,
        note=req.note,
        db=db,
    )
    return {"status": "decided", "approval_id": id, "decision": req.decision.value}
