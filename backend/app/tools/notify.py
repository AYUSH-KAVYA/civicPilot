"""
Notification Tool: notify
Delivers citizen notifications across chat, SMS, and email.
Stores all communications in DB for the citizen sandbox inbox,
and sends real emails via Resend when RESEND_API_KEY is configured.
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import now as clock_now
from backend.app.core.config import get_settings
from backend.app.core.events import mask_contact
from backend.app.db.models import CitizenModel, NotificationModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.tools.registry import tools

# Standard notification templates
TEMPLATES: Dict[str, str] = {
    "case_received": "Hello! Your grievance #{case_id} has been registered and is being reviewed by city intake.",
    "case_triaged": "Update on case #{case_id}: Assigned to {department} (Ward: {ward}). Priority: {urgency}. Target response within {deadline_hours} hours.",
    "crew_dispatched": "Field update for #{case_id}: Response crew {crew_name} has been dispatched to your location.",
    "needs_info": "Notice for case #{case_id}: Our intake team needs additional information: {missing_info}. Please reply in this chat.",
    "repair_completed": "Work completed for #{case_id}! A crew has finished repairs. Please review the repair photo and confirm resolution.",
    "case_closed": "Case #{case_id} is now verified and closed. Thank you for reporting this to Metroville City Services!",
    "approval_required": "Administrative update: Case #{case_id} requires supervisor approval before work proceeds.",
}


def render_template(template_name: str, variables: Dict[str, Any]) -> str:
    """Render notification text from template name or fallback to raw string."""
    fmt = TEMPLATES.get(template_name, template_name)
    try:
        return fmt.format(**variables)
    except KeyError:
        return fmt


async def send_resend_email(to_email: str, subject: str, body: str) -> bool:
    """Send live email via Resend API if API key is configured."""
    settings = get_settings()
    if not settings.RESEND_API_KEY:
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "from": "CivicPilot <notifications@civicpilot.dev>",
        "to": [to_email],
        "subject": subject,
        "text": body,
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[notify warning] Resend email send failed: {e}")
        return False


@tools.register("notify")
async def notify(
    case_id: str,
    channel: str = "chat",  # chat, sms, email
    template: str = "case_received",
    vars: Optional[Dict[str, Any]] = None,
    db: Optional[AsyncSession] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Deliver notification to citizen.
    Persists to DB (notifications table) and optionally dispatches via Resend.
    """
    template_vars = dict(vars or {})
    template_vars.setdefault("case_id", case_id)
    message_body = render_template(template, template_vars)

    async def _execute(session: AsyncSession) -> Dict[str, Any]:
        # Retrieve citizen contact if available
        citizen_stmt = select(CitizenModel).where(CitizenModel.case_id == case_id)
        res = await session.execute(citizen_stmt)
        citizen = res.scalars().first()

        raw_contact = citizen.raw_contact if citizen else "unknown"
        masked_contact = citizen.masked_contact if citizen else mask_contact(raw_contact)

        notification_id = f"notif-{uuid.uuid4().hex[:8]}"
        status = "sent"

        # If email channel and configured, attempt dispatch
        if channel == "email" and "@" in raw_contact:
            email_sent = await send_resend_email(
                to_email=raw_contact,
                subject=f"CivicPilot Update: Case #{case_id}",
                body=message_body,
            )
            if not email_sent:
                status = "sent_sandbox_only"

        notification = NotificationModel(
            id=notification_id,
            case_id=case_id,
            channel=channel,
            template=template,
            vars=template_vars,
            recipient_masked=masked_contact,
            status=status,
            sent_at=clock_now(),
        )
        session.add(notification)
        await session.commit()

        return {
            "notification_id": notification.id,
            "case_id": case_id,
            "channel": channel,
            "template": template,
            "message": message_body,
            "recipient_masked": masked_contact,
            "status": status,
            "sent_at": notification.sent_at.isoformat(),
        }

    if db is not None:
        return await _execute(db)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute(session)
