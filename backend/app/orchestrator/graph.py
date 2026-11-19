"""
CivicPilot Orchestrator: Agent Graph Runner.
Implements the asynchronous multi-agent graph with:
- Shared CaseState persisted after every node execution.
- Per-node timeouts and exponential-backoff retries.
- Per-case lock preventing concurrent runs on the same case.
- Maximum-iteration loop breaker (MAX_ITERATIONS).
- Guardrails integration (confidence threshold, risk tiers).
- Clean stop conditions (CLOSED, NEEDS_HUMAN, AWAITING_CONFIRMATION, awaiting_approval).
Source of truth: docs/CONTRACT.md Section 1, 6.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.agents.action as action_agent
import backend.app.agents.evaluator as evaluator_agent
from backend.app.adaptation.rules import (
    adapt_deadline_imminent,
    adapt_duplicate_cluster,
    adapt_ticket_rejection,
)
from backend.app.core.clock import now as clock_now
from backend.app.core.events import emit_event
from backend.app.db.models import CaseModel
from backend.app.db.session import AsyncSessionLocal
from backend.app.guardrails.confidence import check_and_apply_confidence_guardrail
from backend.app.orchestrator.context import AgentContext
from backend.app.schemas import (
    AgentName,
    CaseStatus,
    Phase,
    StepStatus,
)

logger = logging.getLogger("civicpilot.orchestrator")

# Constants
NODE_TIMEOUT = 30.0
NODE_MAX_RETRIES = 2
MAX_ITERATIONS = 25

# Concurrency Locks
_case_locks: Dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()


async def get_case_lock(case_id: str) -> asyncio.Lock:
    """Retrieve or create an asyncio.Lock for the given case_id."""
    async with _global_lock:
        if case_id not in _case_locks:
            _case_locks[case_id] = asyncio.Lock()
        return _case_locks[case_id]


class DictProxy:
    """Wrapper providing both attribute and dictionary access for agents."""
    def __init__(self, data: Dict[str, Any]) -> None:
        object.__setattr__(self, "_data", data)

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            val = self._data[name]
            if isinstance(val, dict):
                return DictProxy(val)
            return val
        return None

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, val: Any) -> None:
        self._data[key] = val

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def model_dump(self) -> Dict[str, Any]:
        return self._data

    def __contains__(self, key: str) -> bool:
        return key in self._data


class AgentGraph:
    """
    Executes the multi-agent graph workflow for a case.
    """
    def __init__(self, case_id: str, db: Optional[AsyncSession] = None) -> None:
        self.case_id = case_id
        self._external_db = db

    async def run(
        self,
        start_node: str = "intake",
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the agent graph starting from start_node under a per-case lock.
        """
        lock = await get_case_lock(self.case_id)
        async with lock:
            if self._external_db is not None:
                return await self._run_loop(self._external_db, start_node, payload)
            else:
                async with AsyncSessionLocal() as session:
                    return await self._run_loop(session, start_node, payload)

    async def _run_loop(
        self,
        session: AsyncSession,
        current_node: Optional[str],
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Core graph execution loop."""
        case = await session.get(CaseModel, self.case_id)
        if not case:
            raise ValueError(f"Case '{self.case_id}' not found in database.")

        state: Dict[str, Any] = dict(case.state)
        ctx = AgentContext.create(db=session)

        iteration_count = 0

        while current_node and iteration_count < MAX_ITERATIONS:
            iteration_count += 1
            node_name = current_node
            logger.info(f"[Case {self.case_id}] Executing node: {node_name} (iteration {iteration_count})")

            # 1. Execute node with retry and timeout
            result, next_node = await self._execute_node_with_retry(node_name, state, ctx, payload)
            payload = None  # Consume payload after first node

            # 2. Apply state patch
            if result and hasattr(result, "state_patch") and result.state_patch:
                self._apply_patch(state, result.state_patch)
            elif isinstance(result, dict) and "state_patch" in result:
                self._apply_patch(state, result["state_patch"])

            # Ensure intake.location.address is non-null string per CaseState schema
            if "intake" in state and isinstance(state["intake"], dict):
                loc = state["intake"].setdefault("location", {})
                if not loc.get("address"):
                    loc["address"] = state.get("raw", {}).get("address_text") or "Metroville District"

            # 3. Check Confidence Guardrail on perception & reasoning nodes
            if node_name in ("intake", "triage") and result and hasattr(result, "confidence"):
                confidence = float(result.confidence)
                tripped, packet = await check_and_apply_confidence_guardrail(
                    state,
                    confidence=confidence,
                    agent_name=node_name,
                    ctx=ctx,
                    db=session,
                )
                if tripped:
                    logger.info(f"[Case {self.case_id}] Confidence guardrail tripped ({confidence:.2f}). Routing to NEEDS_HUMAN.")
                    await self._persist_state(session, case, state)
                    return state

            # 4. Check Duplicate Complaints Clustering (Adaptation Rule D) during triage
            if node_name == "triage":
                cluster_merged = await self._check_duplicate_cluster(state, ctx, session)
                if cluster_merged:
                    logger.info(f"[Case {self.case_id}] Clustered and merged into area work order. Closing.")
                    await self._persist_state(session, case, state)
                    return state

            # 5. Persist CaseState after EVERY node
            await self._persist_state(session, case, state)

            # 6. Check Stop Conditions
            status_val = state.get("status", "")
            if status_val in (
                CaseStatus.CLOSED.value,
                CaseStatus.NEEDS_HUMAN.value,
                CaseStatus.AWAITING_CONFIRMATION.value,
            ):
                logger.info(f"[Case {self.case_id}] Reached terminal/pause status: {status_val}. Halting graph.")
                break

            # Check if any step is awaiting officer approval
            plan = state.get("plan", {})
            steps = plan.get("steps", []) if isinstance(plan, dict) else getattr(plan, "steps", [])
            has_pending_approval = any(
                (s.get("status") if isinstance(s, dict) else s.status) == StepStatus.awaiting_approval.value
                for s in steps
            )
            if has_pending_approval:
                logger.info(f"[Case {self.case_id}] Awaiting officer approval. Pausing graph.")
                break

            # Transition to next node
            current_node = next_node

        # Check loop breaker
        if iteration_count >= MAX_ITERATIONS:
            logger.warning(f"[Case {self.case_id}] Loop breaker tripped! Exceeded {MAX_ITERATIONS} iterations.")
            state["status"] = CaseStatus.NEEDS_HUMAN.value
            flags = state.setdefault("flags", {})
            flags["needs_human"] = True
            flags["human_reason"] = f"Loop breaker triggered: exceeded maximum allowed iterations ({MAX_ITERATIONS})."

            await emit_event(
                case_id=self.case_id,
                agent=AgentName.orchestrator,
                phase=Phase.guardrail,
                summary=f"Loop breaker triggered: exceeded {MAX_ITERATIONS} iterations, routed to NEEDS_HUMAN",
                detail={"iterations": iteration_count},
                db=session,
            )
            await self._persist_state(session, case, state)

        return state

    async def _execute_node_with_retry(
        self,
        node_name: str,
        state: Dict[str, Any],
        ctx: AgentContext,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Optional[str]]:
        """Run a single node with timeout and exponential backoff retry."""
        last_error: Optional[Exception] = None

        for attempt in range(1, NODE_MAX_RETRIES + 1):
            try:
                result = await asyncio.wait_for(
                    self._dispatch_node(node_name, state, ctx, payload),
                    timeout=NODE_TIMEOUT,
                )
                next_node = getattr(result, "next", None)
                if isinstance(result, dict) and "next" in result:
                    next_node = result["next"]
                return result, next_node

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Node '{node_name}' timed out after {NODE_TIMEOUT}s (attempt {attempt}/{NODE_MAX_RETRIES})")
                logger.warning(str(last_error))
            except Exception as e:
                last_error = e
                logger.warning(f"Node '{node_name}' error (attempt {attempt}/{NODE_MAX_RETRIES}): {e}")

            if attempt < NODE_MAX_RETRIES:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        # Retries exhausted -> route to human
        logger.error(f"Node '{node_name}' failed after {NODE_MAX_RETRIES} attempts. Handing off to human.")
        state["status"] = CaseStatus.NEEDS_HUMAN.value
        flags = state.setdefault("flags", {})
        flags["needs_human"] = True
        flags["human_reason"] = f"Node '{node_name}' failed execution: {str(last_error)}"

        await emit_event(
            case_id=self.case_id,
            agent=AgentName.orchestrator,
            phase=Phase.guardrail,
            summary=f"Node '{node_name}' failed after retries: {str(last_error)}",
            detail={"node": node_name, "error": str(last_error)},
            db=ctx.db,
        )
        return None, None

    async def _dispatch_node(
        self,
        node_name: str,
        state: Dict[str, Any],
        ctx: AgentContext,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Call the actual agent or adaptation routine for node_name."""
        proxy_state = DictProxy(state)

        if node_name == "intake":
            from agents.intake import run as intake_run
            return await intake_run(proxy_state, ctx)

        elif node_name == "triage":
            from agents.triage import run as triage_run
            res = await triage_run(proxy_state, ctx)
            # Calculate deadline_at from triage.deadline_hours
            if hasattr(res, "state_patch") and "triage" in res.state_patch:
                triage_data = res.state_patch["triage"]
                hrs = float(triage_data.get("deadline_hours", 24))
                deadline = clock_now() + timedelta(hours=hrs)
                state["deadline_at"] = deadline.isoformat()
            return res

        elif node_name == "planner":
            from agents.planner import run as planner_run
            return await planner_run(proxy_state, ctx)

        elif node_name == "action":
            return await action_agent.run(proxy_state, ctx)

        elif node_name == "evaluator":
            return await evaluator_agent.run(proxy_state, ctx)

        elif node_name == "adapt_ticket_rejection":
            reason = (payload or {}).get("reason", "Department ticket rejected")
            patch = await adapt_ticket_rejection(state, reason, ctx)
            return type("AdaptResult", (), {"state_patch": patch, "next": "action", "confidence": 1.0})()

        elif node_name == "adapt_deadline_imminent":
            reason = (payload or {}).get("reason", "Deadline imminent")
            patch = await adapt_deadline_imminent(state, reason, ctx)
            return type("AdaptResult", (), {"state_patch": patch, "next": "action", "confidence": 1.0})()

        else:
            raise KeyError(f"Unknown graph node '{node_name}'")

    async def _check_duplicate_cluster(
        self,
        state: Dict[str, Any],
        ctx: AgentContext,
        session: AsyncSession,
    ) -> bool:
        """Check for duplicate complaints cluster (Adaptation Rule D)."""
        raw = state.get("raw", {})
        text = raw.get("text", "")
        lat = raw.get("lat")
        lng = raw.get("lng")

        if not text:
            return False

        tools = getattr(ctx, "tools", None)
        similar_cases: List[Dict[str, Any]] = []
        if tools and hasattr(tools, "call"):
            try:
                similar_cases = await tools.call(
                    "similar_cases",
                    {"text": text, "lat": lat, "lng": lng, "radius_m": 500, "k": 3},
                    case_id=self.case_id,
                    agent=AgentName.orchestrator,
                    db=session,
                )
            except Exception:
                similar_cases = []

        if not similar_cases:
            return False

        # Look for existing active complaint with high match
        for sim in similar_cases:
            match_id = sim.get("case_id") or sim.get("id")
            score = float(sim.get("score") or sim.get("similarity", 0.0))
            if match_id and match_id != self.case_id and score >= 0.85:
                # Found high similarity duplicate in radius!
                await adapt_duplicate_cluster(state, match_id, score, ctx)
                return True

        return False

    def _apply_patch(self, state: Dict[str, Any], patch: Dict[str, Any]) -> None:
        """Merge state_patch into state dict."""
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(state.get(k), dict):
                state[k].update(v)
            else:
                state[k] = v

    async def _persist_state(
        self,
        session: AsyncSession,
        case: CaseModel,
        state: Dict[str, Any],
    ) -> None:
        """Persist state updates and top-level indexed columns to DB."""
        case.state = dict(state)
        case.status = state.get("status", case.status)
        case.updated_at = clock_now()

        # Update deadline_at if present
        deadline_raw = state.get("deadline_at")
        if deadline_raw and isinstance(deadline_raw, str):
            try:
                case.deadline_at = datetime.fromisoformat(deadline_raw.replace("Z", "+00:00"))
            except Exception:
                pass
        elif isinstance(deadline_raw, datetime):
            case.deadline_at = deadline_raw

        # Update triage indexed fields if present
        triage = state.get("triage", {})
        if isinstance(triage, dict):
            if "urgency" in triage:
                case.urgency = triage["urgency"]
            if "department_id" in triage:
                case.department_id = triage["department_id"]
            if "ward_id" in triage:
                case.ward_id = triage["ward_id"]
            if "office_id" in triage:
                case.office_id = triage["office_id"]

        session.add(case)
        await session.commit()
