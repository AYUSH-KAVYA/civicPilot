"""
CivicPilot Orchestrator: AgentContext
Provides the runtime context passed to each agent's async run() method.
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.clock import clock
from backend.app.core.config import get_settings
from backend.app.core.events import emit_event
from backend.app.llm.client import GeminiClient
from backend.app.schemas import AgentName, Phase
from backend.app.tools.registry import tools as default_tools_registry

# Register dependency tools from P2 (similar_cases, policy_search, parse_media) if not yet registered
try:
    from kb.similar_cases import similar_cases as _kb_similar_cases
    if not default_tools_registry.get("similar_cases"):
        default_tools_registry.register_fn("similar_cases", _kb_similar_cases)
except Exception:
    pass

try:
    from kb.search import policy_search as _kb_policy_search
    if not default_tools_registry.get("policy_search"):
        default_tools_registry.register_fn("policy_search", _kb_policy_search)
except Exception:
    pass

try:
    from tools.parse_media import parse_media as _tools_parse_media
    if not default_tools_registry.get("parse_media"):
        default_tools_registry.register_fn("parse_media", _tools_parse_media)
except Exception:
    pass


class ContextEmitHelper:
    """Helper enabling both positional and keyword invocation for ctx.emit."""
    def __init__(self, db: Optional[AsyncSession] = None) -> None:
        self.db = db

    async def __call__(
        self,
        case_id: str,
        agent: AgentName | str,
        phase: Phase | str,
        summary: str,
        detail: Optional[Dict[str, Any]] = None,
        tool_name: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        session = kwargs.get("db", self.db)
        return await emit_event(
            case_id=case_id,
            agent=agent,
            phase=phase,
            summary=summary,
            detail=detail,
            tool_name=tool_name,
            reason=reason,
            db=session,
        )


@dataclass
class AgentContext:
    db: Optional[AsyncSession] = None
    llm: Any = None
    tools: Any = None
    emit: Any = None
    settings: Any = None
    clock: Any = None

    @classmethod
    def create(cls, db: Optional[AsyncSession] = None) -> "AgentContext":
        cfg = get_settings()
        return cls(
            db=db,
            llm=GeminiClient(settings=cfg.model_dump()),
            tools=default_tools_registry,
            emit=ContextEmitHelper(db=db),
            settings=cfg,
            clock=clock,
        )
