"""
Ticketing Tool for CivicPilot.
Handles municipal work ticket creation, nearest-crew assignment by distance,
ticket updates, status checks, and crew discovery.
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import CaseModel, CrewModel, TicketModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.tools.registry import tools


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


@tools.register("create_ticket")
async def create_ticket(
    case_id: str,
    department_id: str,
    priority: str = "medium",
    due_at: Optional[datetime] = None,
    notes: Optional[List[str]] = None,
    crew_id: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a new municipal department ticket."""
    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        ticket_id = f"tkt-{uuid.uuid4().hex[:8]}"
        initial_notes = notes or ["Ticket created."]

        ticket = TicketModel(
            id=ticket_id,
            case_id=case_id,
            department_id=department_id,
            crew_id=None if crew_id == "nearest" else crew_id,
            status="open",
            priority=priority,
            due_at=due_at,
            notes=initial_notes,
        )
        session.add(ticket)
        await session.flush()

        if crew_id == "nearest":
            await _assign_nearest_crew(session, ticket)

        # Update case state JSON tickets array
        case = await session.get(CaseModel, case_id)
        if case and case.state:
            state = dict(case.state)
            tickets_list = state.get("tickets", [])
            tickets_list.append({
                "id": ticket.id,
                "department_id": ticket.department_id,
                "status": ticket.status,
                "crew_id": ticket.crew_id,
                "priority": ticket.priority,
                "due_at": ticket.due_at.isoformat() if ticket.due_at else None,
                "notes": ticket.notes,
            })
            state["tickets"] = tickets_list
            case.state = state
            session.add(case)

        await session.commit()
        return {
            "id": ticket.id,
            "case_id": ticket.case_id,
            "department_id": ticket.department_id,
            "crew_id": ticket.crew_id,
            "status": ticket.status,
            "priority": ticket.priority,
            "due_at": ticket.due_at.isoformat() if ticket.due_at else None,
            "notes": ticket.notes,
        }

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)


async def _assign_nearest_crew(session: AsyncSession, ticket: TicketModel) -> Optional[CrewModel]:
    """Find and assign the nearest available crew for the ticket's case location."""
    # Retrieve case location
    case = await session.get(CaseModel, ticket.case_id)
    case_lat, case_lng = 37.750, -122.420  # Metroville default
    if case and case.state:
        raw = case.state.get("raw", {})
        if raw.get("lat") is not None and raw.get("lng") is not None:
            case_lat, case_lng = float(raw["lat"]), float(raw["lng"])
        elif case.state.get("intake", {}).get("location"):
            loc = case.state["intake"]["location"]
            if loc.get("lat") is not None and loc.get("lng") is not None:
                case_lat, case_lng = float(loc["lat"]), float(loc["lng"])

    # Query crews for department
    stmt = select(CrewModel).where(CrewModel.department_id == ticket.department_id)
    result = await session.execute(stmt)
    all_crews = result.scalars().all()

    # Prefer available crews
    available_crews = [c for c in all_crews if c.status == "available"]
    candidate_crews = available_crews if available_crews else all_crews

    if not candidate_crews:
        return None

    # Sort by Haversine distance
    candidate_crews.sort(
        key=lambda c: haversine_distance_km(case_lat, case_lng, c.lat, c.lng)
    )
    nearest = candidate_crews[0]

    ticket.crew_id = nearest.id
    ticket.status = "assigned"
    nearest.status = "assigned"
    ticket.notes.append(f"Assigned nearest crew {nearest.name} ({nearest.id}).")
    session.add(ticket)
    session.add(nearest)
    return nearest


@tools.register("assign_crew")
async def assign_crew(
    ticket_id: str,
    crew_id: str = "nearest",
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Assign a crew (by ID or 'nearest') to an existing ticket."""
    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        ticket = await session.get(TicketModel, ticket_id)
        if not ticket:
            raise KeyError(f"Ticket '{ticket_id}' not found.")

        if crew_id == "nearest":
            crew = await _assign_nearest_crew(session, ticket)
        else:
            crew = await session.get(CrewModel, crew_id)
            if not crew:
                raise KeyError(f"Crew '{crew_id}' not found.")
            ticket.crew_id = crew.id
            ticket.status = "assigned"
            crew.status = "assigned"
            ticket.notes.append(f"Assigned crew {crew.name} ({crew.id}).")
            session.add(ticket)
            session.add(crew)

        # Update case state if present
        case = await session.get(CaseModel, ticket.case_id)
        if case and case.state:
            state = dict(case.state)
            for t in state.get("tickets", []):
                if t.get("id") == ticket.id:
                    t["crew_id"] = ticket.crew_id
                    t["status"] = ticket.status
                    t["notes"] = ticket.notes
            case.state = state
            session.add(case)

        await session.commit()
        return {
            "ticket_id": ticket.id,
            "crew_id": ticket.crew_id,
            "crew_name": crew.name if crew else None,
            "status": ticket.status,
            "notes": ticket.notes,
        }

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)


@tools.register("update_ticket")
async def update_ticket(
    ticket_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    note: Optional[str] = None,
    notes: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Update ticket status, priority, or append notes."""
    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        ticket = await session.get(TicketModel, ticket_id)
        if not ticket:
            raise KeyError(f"Ticket '{ticket_id}' not found.")

        if status:
            ticket.status = status
        if priority:
            ticket.priority = priority
        if note:
            ticket.notes.append(note)
        if notes:
            ticket.notes.extend(notes)

        # If ticket completed or rejected, free up the crew
        if status in ("completed", "rejected") and ticket.crew_id:
            crew = await session.get(CrewModel, ticket.crew_id)
            if crew:
                crew.status = "available"
                session.add(crew)

        session.add(ticket)

        # Sync case state
        case = await session.get(CaseModel, ticket.case_id)
        if case and case.state:
            state = dict(case.state)
            for t in state.get("tickets", []):
                if t.get("id") == ticket.id:
                    t["status"] = ticket.status
                    t["priority"] = ticket.priority
                    t["notes"] = ticket.notes
            case.state = state
            session.add(case)

        await session.commit()
        return {
            "id": ticket.id,
            "status": ticket.status,
            "priority": ticket.priority,
            "crew_id": ticket.crew_id,
            "notes": ticket.notes,
        }

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)


@tools.register("get_ticket")
async def get_ticket(
    ticket_id: str,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Retrieve details for a specific ticket."""
    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        ticket = await session.get(TicketModel, ticket_id)
        if not ticket:
            raise KeyError(f"Ticket '{ticket_id}' not found.")
        return {
            "id": ticket.id,
            "case_id": ticket.case_id,
            "department_id": ticket.department_id,
            "crew_id": ticket.crew_id,
            "status": ticket.status,
            "priority": ticket.priority,
            "due_at": ticket.due_at.isoformat() if ticket.due_at else None,
            "notes": ticket.notes,
        }

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)


@tools.register("list_crews")
async def list_crews(
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """List crews, optionally filtered by department and status."""
    async def _execute(session: AsyncSession) -> List[Dict[str, Any]]:
        stmt = select(CrewModel)
        if department_id:
            stmt = stmt.where(CrewModel.department_id == department_id)
        if status:
            stmt = stmt.where(CrewModel.status == status)

        result = await session.execute(stmt)
        crews = result.scalars().all()
        return [
            {
                "id": c.id,
                "department_id": c.department_id,
                "name": c.name,
                "lat": c.lat,
                "lng": c.lng,
                "status": c.status,
                "contact": c.contact,
            }
            for c in crews
        ]

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)
