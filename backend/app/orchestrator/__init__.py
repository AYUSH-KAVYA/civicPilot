"""
CivicPilot Orchestrator Package.
Exposes the multi-agent graph orchestrator and public API:
- start_case
- resume_case
- handle_citizen_message
- handle_citizen_confirmation
- handle_approval
- handle_sandbox_signal
- AgentGraph
- AgentContext
"""

from backend.app.orchestrator.context import AgentContext
from backend.app.orchestrator.graph import AgentGraph
from backend.app.orchestrator.service import (
    handle_approval,
    handle_citizen_confirmation,
    handle_citizen_message,
    handle_sandbox_signal,
    resume_case,
    start_case,
)

__all__ = [
    "start_case",
    "resume_case",
    "handle_citizen_message",
    "handle_citizen_confirmation",
    "handle_approval",
    "handle_sandbox_signal",
    "AgentGraph",
    "AgentContext",
]
