"""
Action Agent for CivicPilot.
Executes plan steps in dependency order through tools.call,
updates step status, executes step fallback on tool failure,
enforces risk tiers (pausing for critical approvals and alerting for sensitive operations).
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.app.core.events import emit_event
from backend.app.guardrails.risk_tiers import enforce_risk_tier
from backend.app.schemas import (
    AgentName,
    CaseState,
    CaseStatus,
    Phase,
    StepStatus,
)

logger = logging.getLogger("civicpilot.action")


@dataclass
class AgentResult:
    state_patch: Dict[str, Any]
    next: Optional[str]
    confidence: float


async def run(state: CaseState | Any, ctx: Any) -> AgentResult:
    """
    Execute pending plan steps in dependency order.
    """
    case_id = state.get("id") if isinstance(state, dict) else state.id

    # Parse plan from state
    plan_raw = state.get("plan") if isinstance(state, dict) else state.plan
    if hasattr(plan_raw, "model_dump"):
        plan_dict = plan_raw.model_dump()
    elif isinstance(plan_raw, dict):
        plan_dict = dict(plan_raw)
    else:
        plan_dict = {"version": 1, "steps": []}

    steps_data: List[Dict[str, Any]] = plan_dict.get("steps", [])

    # Existing tickets list
    tickets_raw = state.get("tickets", []) if isinstance(state, dict) else (state.tickets or [])
    tickets_list: List[Dict[str, Any]] = [
        t.model_dump() if hasattr(t, "model_dump") else dict(t)
        for t in tickets_raw
    ]

    has_approval_pause = False
    progress_made = True

    # Dependency execution loop: run ready steps until no more can run or blocked by approval
    while progress_made and not has_approval_pause:
        progress_made = False

        # Status map for dependencies
        step_status_map = {s["id"]: s.get("status", "pending") for s in steps_data}

        for step in steps_data:
            step_id = step["id"]
            status = step.get("status", "pending")

            if status != StepStatus.pending.value:
                continue

            # Check dependencies
            depends_on = step.get("depends_on", [])
            deps_done = all(step_status_map.get(dep) == StepStatus.done.value for dep in depends_on)
            deps_failed = any(
                step_status_map.get(dep) in (StepStatus.failed.value, StepStatus.skipped.value)
                for dep in depends_on
            )

            if deps_failed:
                # If dependency failed, skip this step
                step["status"] = StepStatus.skipped.value
                step_status_map[step_id] = StepStatus.skipped.value
                progress_made = True
                await emit_event(
                    case_id=case_id,
                    agent=AgentName.action,
                    phase=Phase.act,
                    summary=f"Skipped step '{step.get('title', step_id)}' due to failed dependency",
                    detail={"step_id": step_id, "depends_on": depends_on},
                    db=getattr(ctx, "db", None),
                )
                continue

            if not deps_done:
                # Dependencies still running or pending
                continue

            # Step is ready! Check risk tier first
            requires_approval, approval_id = await enforce_risk_tier(
                step,
                case_id=case_id,
                ctx=ctx,
                db=getattr(ctx, "db", None),
            )

            if requires_approval:
                # Paused for critical approval!
                step["status"] = StepStatus.awaiting_approval.value
                step_status_map[step_id] = StepStatus.awaiting_approval.value
                has_approval_pause = True
                progress_made = True
                break

            # Execute tool
            step["status"] = StepStatus.running.value
            step_status_map[step_id] = StepStatus.running.value

            tool_name = step.get("tool", "")
            tool_args = dict(step.get("args", {}))
            # Ensure case_id is passed if tool needs it
            if "case_id" not in tool_args:
                tool_args["case_id"] = case_id

            # Contextual parameter resolution for inter-step dependencies
            if tool_name == "create_ticket" and "department_id" not in tool_args:
                triage_dept = None
                triage = state.get("triage") if isinstance(state, dict) else getattr(state, "triage", None)
                if hasattr(triage, "department_id"):
                    triage_dept = triage.department_id
                elif isinstance(triage, dict):
                    triage_dept = triage.get("department_id")
                if not triage_dept and tickets_list:
                    triage_dept = tickets_list[-1].get("department_id")
                tool_args["department_id"] = triage_dept or "water"

            if tool_name == "assign_crew" and "ticket_id" not in tool_args:
                if tickets_list:
                    tool_args["ticket_id"] = tickets_list[-1].get("id")

            if tool_name == "schedule_check" and "run_at" not in tool_args:
                from datetime import datetime, timedelta

                from backend.app.core.clock import now as clock_now
                due_raw = step.get("due_at")
                if due_raw and isinstance(due_raw, str):
                    try:
                        tool_args["run_at"] = datetime.fromisoformat(due_raw.replace("Z", "+00:00"))
                    except Exception:
                        tool_args["run_at"] = clock_now() + timedelta(hours=4)
                elif isinstance(due_raw, datetime):
                    tool_args["run_at"] = due_raw
                else:
                    tool_args["run_at"] = clock_now() + timedelta(hours=4)

            tool_error: Optional[Exception] = None
            tool_result: Any = None

            try:
                tools_registry = getattr(ctx, "tools", None)
                if tools_registry and hasattr(tools_registry, "call"):
                    tool_result = await tools_registry.call(
                        tool_name,
                        tool_args,
                        case_id=case_id,
                        agent=AgentName.action,
                        db=getattr(ctx, "db", None),
                    )
                else:
                    # Mock/stub execution if tools registry not present
                    tool_result = {"status": "ok", "mock": True}

                step["status"] = StepStatus.done.value
                step["result"] = tool_result
                step_status_map[step_id] = StepStatus.done.value
                progress_made = True

                # If ticket was created, record it
                if tool_name == "create_ticket" and isinstance(tool_result, dict) and "id" in tool_result:
                    tickets_list.append(tool_result)

                await emit_event(
                    case_id=case_id,
                    agent=AgentName.action,
                    phase=Phase.act,
                    summary=f"Action step completed: {step.get('title', step_id)}",
                    detail={"step_id": step_id, "tool": tool_name, "result": tool_result},
                    tool_name=tool_name,
                    db=getattr(ctx, "db", None),
                )

            except Exception as e:
                tool_error = e
                logger.warning(f"Step {step_id} ({tool_name}) failed: {e}. Checking fallback.")

                # Try fallback
                fallback = step.get("fallback")
                if fallback and isinstance(fallback, dict) and fallback.get("tool"):
                    fb_tool = fallback["tool"]
                    fb_args = dict(fallback.get("args", {}))
                    if "case_id" not in fb_args:
                        fb_args["case_id"] = case_id

                    try:
                        fb_result = await ctx.tools.call(
                            fb_tool,
                            fb_args,
                            case_id=case_id,
                            agent=AgentName.action,
                            db=getattr(ctx, "db", None),
                        )
                        step["status"] = StepStatus.done.value
                        step["result"] = {"fallback_executed": True, "result": fb_result}
                        step_status_map[step_id] = StepStatus.done.value
                        progress_made = True

                        await emit_event(
                            case_id=case_id,
                            agent=AgentName.action,
                            phase=Phase.act,
                            summary=f"Step '{step.get('title', step_id)}' recovered using fallback {fb_tool}",
                            detail={"step_id": step_id, "original_error": str(tool_error), "fallback_result": fb_result},
                            tool_name=fb_tool,
                            reason="Step failure fallback",
                            db=getattr(ctx, "db", None),
                        )
                    except Exception as fb_err:
                        step["status"] = StepStatus.failed.value
                        step["result"] = {"error": str(tool_error), "fallback_error": str(fb_err)}
                        step_status_map[step_id] = StepStatus.failed.value
                        progress_made = True

                        await emit_event(
                            case_id=case_id,
                            agent=AgentName.action,
                            phase=Phase.act,
                            summary=f"Step '{step.get('title', step_id)}' failed with fallback error: {fb_err}",
                            detail={"step_id": step_id, "error": str(tool_error), "fallback_error": str(fb_err)},
                            tool_name=tool_name,
                            db=getattr(ctx, "db", None),
                        )
                else:
                    step["status"] = StepStatus.failed.value
                    step["result"] = {"error": str(tool_error)}
                    step_status_map[step_id] = StepStatus.failed.value
                    progress_made = True

                    await emit_event(
                        case_id=case_id,
                        agent=AgentName.action,
                        phase=Phase.act,
                        summary=f"Step '{step.get('title', step_id)}' failed: {tool_error}",
                        detail={"step_id": step_id, "error": str(tool_error)},
                        tool_name=tool_name,
                        db=getattr(ctx, "db", None),
                    )

    # Determine next node in graph
    if has_approval_pause:
        next_node = None  # Paused awaiting officer approval
    else:
        # Check if all steps done or if we should evaluate
        next_node = "evaluator"

    plan_dict["steps"] = steps_data

    state_patch: Dict[str, Any] = {
        "status": CaseStatus.IN_PROGRESS.value,
        "plan": plan_dict,
        "tickets": tickets_list,
    }

    return AgentResult(
        state_patch=state_patch,
        next=next_node,
        confidence=1.0,
    )
