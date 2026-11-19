"""
Department Sandbox Service.
Simulates external department operations and field crews for live demos and testing.
Exposes endpoints to simulate ticket rejections, crew check-ins, no-shows, and repair photos.
Source of truth: docs/CONTRACT.md Section 7.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.core.orchestrator_bridge as orchestrator
from backend.app.db.models import CrewModel, TicketModel


class DepartmentSandbox:
    async def reject_ticket(
        self,
        ticket_id: str,
        reason: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Simulate department dispatcher rejecting the work ticket."""
        ticket = await db.get(TicketModel, ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} not found")

        ticket.status = "rejected"
        ticket.notes.append(f"[Sandbox] Department rejected ticket: {reason}")
        if ticket.crew_id:
            crew = await db.get(CrewModel, ticket.crew_id)
            if crew:
                crew.status = "available"
                db.add(crew)
        db.add(ticket)
        await db.commit()

        signal = {
            "type": "ticket_rejected",
            "ticket_id": ticket.id,
            "department_id": ticket.department_id,
            "reason": reason,
        }
        await orchestrator.handle_sandbox_signal(case_id=ticket.case_id, signal=signal, db=db)
        return {"status": "success", "signal": signal}

    async def crew_checkin(
        self,
        ticket_id: str,
        lat: Optional[float],
        lng: Optional[float],
        notes: Optional[str],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Simulate field crew checking in upon arrival at the site."""
        ticket = await db.get(TicketModel, ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} not found")

        ticket.status = "in_progress"
        msg = f"[Sandbox] Crew checked in at site. Notes: {notes or 'Arrived on location'}"
        ticket.notes.append(msg)
        db.add(ticket)
        await db.commit()

        signal = {
            "type": "crew_checked_in",
            "ticket_id": ticket.id,
            "crew_id": ticket.crew_id,
            "lat": lat,
            "lng": lng,
            "notes": notes or "Crew arrived at site.",
        }
        await orchestrator.handle_sandbox_signal(case_id=ticket.case_id, signal=signal, db=db)
        return {"status": "success", "signal": signal}

    async def crew_no_show(
        self,
        ticket_id: str,
        reason: Optional[str],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Simulate assigned crew failing to show up or abandoning work."""
        ticket = await db.get(TicketModel, ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} not found")

        msg = f"[Sandbox] Crew NO-SHOW reported: {reason or 'Uncontactable'}"
        ticket.notes.append(msg)
        db.add(ticket)
        await db.commit()

        signal = {
            "type": "crew_no_show",
            "ticket_id": ticket.id,
            "crew_id": ticket.crew_id,
            "reason": reason or "Crew failed to appear on site.",
        }
        await orchestrator.handle_sandbox_signal(case_id=ticket.case_id, signal=signal, db=db)
        return {"status": "success", "signal": signal}

    async def upload_repair_photo(
        self,
        ticket_id: str,
        photo_url: str,
        notes: Optional[str],
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Simulate repair completion with uploaded proof photo."""
        ticket = await db.get(TicketModel, ticket_id)
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ticket {ticket_id} not found")

        ticket.status = "completed"
        msg = f"[Sandbox] Repair completed. Photo: {photo_url}. Notes: {notes or 'Fixed'}"
        ticket.notes.append(msg)

        if ticket.crew_id:
            crew = await db.get(CrewModel, ticket.crew_id)
            if crew:
                crew.status = "available"
                db.add(crew)

        db.add(ticket)
        await db.commit()

        signal = {
            "type": "repair_photo_uploaded",
            "ticket_id": ticket.id,
            "crew_id": ticket.crew_id,
            "photo_url": photo_url,
            "notes": notes or "Repairs verified and finished.",
        }
        await orchestrator.handle_sandbox_signal(case_id=ticket.case_id, signal=signal, db=db)
        return {"status": "success", "signal": signal}


sandbox_service = DepartmentSandbox()
