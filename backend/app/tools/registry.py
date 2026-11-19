"""
Tool Registry for CivicPilot.
Central dispatcher for all agent tool executions with timeouts, retries,
and automatic tool_call/tool_result audit event emissions.
Source of truth: docs/CONTRACT.md Section 6.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable, Coroutine, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.events import emit_event
from backend.app.schemas import AgentName, Phase


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    def register(self, name: str) -> Callable:
        """Decorator to register an async tool function by name."""
        def decorator(fn: Callable[..., Coroutine[Any, Any, Any]]) -> Callable:
            self._tools[name] = fn
            return fn
        return decorator

    def register_fn(self, name: str, fn: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        """Register a tool function directly."""
        self._tools[name] = fn

    def get(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    async def call(
        self,
        name: str,
        args: Dict[str, Any],
        case_id: str,
        agent: AgentName | str = AgentName.orchestrator,
        timeout: float = 30.0,
        max_retries: int = 3,
        db: Optional[AsyncSession] = None,
    ) -> Any:
        """
        Execute tool with timeout, retries, and automatic audit event emission.
        """
        tool_fn = self._tools.get(name)
        if not tool_fn:
            raise KeyError(f"Tool '{name}' is not registered in the ToolRegistry.")

        # Emit tool_call event
        await emit_event(
            case_id=case_id,
            agent=agent,
            phase=Phase.tool_call,
            summary=f"Calling tool: {name}",
            detail={"tool": name, "args": args},
            tool_name=name,
            db=db,
        )

        last_error: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                # Check if tool_fn accepts db or case_id kwargs
                sig = inspect.signature(tool_fn)
                kwargs = dict(args)
                if "db" in sig.parameters and "db" not in kwargs:
                    kwargs["db"] = db
                if "case_id" in sig.parameters and "case_id" not in kwargs:
                    kwargs["case_id"] = case_id

                result = await asyncio.wait_for(tool_fn(**kwargs), timeout=timeout)

                # Emit tool_result success event
                result_detail = result if isinstance(result, dict) else {"result": result}
                await emit_event(
                    case_id=case_id,
                    agent=agent,
                    phase=Phase.tool_result,
                    summary=f"Tool {name} completed successfully",
                    detail=result_detail,
                    tool_name=name,
                    db=db,
                )
                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Tool '{name}' timed out after {timeout}s (attempt {attempt}/{max_retries})")
            except Exception as e:
                last_error = e

            if attempt < max_retries:
                await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        # If all retries failed, emit tool_result error event
        err_msg = str(last_error)
        await emit_event(
            case_id=case_id,
            agent=agent,
            phase=Phase.tool_result,
            summary=f"Tool {name} failed: {err_msg}",
            detail={"error": err_msg, "attempts": max_retries},
            tool_name=name,
            reason=err_msg,
            db=db,
        )
        raise last_error or RuntimeError(f"Tool '{name}' failed after {max_retries} attempts.")


# Global tool registry instance
tools = ToolRegistry()
