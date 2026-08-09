"""
Jarvis OS — Execution Engine.

Takes an ``ExecutionPlan`` and runs each step sequentially,
calling tools, collecting results, and updating step statuses.

Spec Volume 3: "AI decides *what* to do. Tools decide *how* to do it."
"""

from __future__ import annotations

from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.planner.planner import ExecutionPlan, PlanStep, StepStatus
from jarvis.tools.base import ToolResult
from jarvis.tools.registry import ToolRegistry
from jarvis.verification.truth_seals import TruthSealManager
from jarvis.verification.verifier import Verifier

logger = structlog.get_logger(__name__)


class Executor:
    """
    Runs execution plans step-by-step.

    For each step:
    1. Resolve the tool from the registry
    2. Execute with the plan's parameters
    3. Verify the result
    4. Update step status
    5. Fire events for monitoring
    """

    def __init__(self, tool_registry: ToolRegistry, verifier: Verifier) -> None:
        self._tools = tool_registry
        self._verifier = verifier
        self._bus = get_event_bus()

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        *,
        on_step_complete: Any | None = None,
    ) -> ExecutionPlan:
        """
        Execute all steps in *plan* in dependency order.

        Returns the updated plan with results filled in.
        *on_step_complete* is an optional async callback(step) for progress.
        """
        logger.info(
            "executor.start",
            goal=plan.goal[:80],
            total_steps=len(plan.steps),
        )

        while True:
            step = plan.next_step
            if step is None:
                break  # All done (or deadlocked)

            await self._execute_step(step)

            if on_step_complete:
                await on_step_complete(step)

        status = "completed" if plan.is_complete else "partial"
        if plan.has_failures:
            status = "completed_with_errors"

        logger.info(
            "executor.finished",
            goal=plan.goal[:80],
            status=status,
            steps_completed=sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED),
            steps_failed=sum(1 for s in plan.steps if s.status == StepStatus.FAILED),
        )

        return plan

    async def _execute_step(self, step: PlanStep) -> None:
        """Execute a single plan step."""
        step.status = StepStatus.RUNNING

        await self._bus.publish(Event(
            type=EventTypes.TOOL_STARTED,
            data={
                "step_id": step.id,
                "tool": step.tool_name,
                "description": step.description,
            },
            source="executor",
        ))

        if not step.tool_name:
            # No tool assigned — this step is informational or AI-handled
            step.status = StepStatus.COMPLETED
            step.result = {"note": "Handled by AI reasoning"}
            return

        tool = self._tools.get(step.tool_name)
        if tool is None:
            step.status = StepStatus.FAILED
            step.error = f"Tool '{step.tool_name}' not found in registry."
            logger.error("executor.tool_not_found", tool=step.tool_name)

            await self._bus.publish(Event(
                type=EventTypes.TOOL_FAILED,
                data={"step_id": step.id, "tool": step.tool_name, "error": step.error},
                source="executor",
            ))
            return

        # Execute the tool
        try:
            result = await tool.execute(**step.tool_params)
        except Exception as exc:
            result = ToolResult(success=False, error=f"Unexpected error: {exc}")
            logger.exception("executor.tool_exception", tool=step.tool_name)

        # Verify the result
        verified = await self._verifier.verify_tool_result(tool, result)

        if result.success and verified:
            if tool.metadata.dangerous:
                seal_id = TruthSealManager.issue_seal(tool.name, step.tool_params, result.output)
                if not result.metadata:
                    result.metadata = {}
                result.metadata["truth_seal"] = seal_id
            
            step.status = StepStatus.COMPLETED
            step.result = result.output
        else:
            step.status = StepStatus.FAILED
            step.error = result.error or "Verification failed"
            step.result = result.output

        event_type = EventTypes.TOOL_COMPLETED if step.status == StepStatus.COMPLETED else EventTypes.TOOL_FAILED
        await self._bus.publish(Event(
            type=event_type,
            data={
                "step_id": step.id,
                "tool": step.tool_name,
                "success": result.success,
                "verified": verified,
                "output_preview": str(result.output)[:200] if result.output else None,
            },
            source="executor",
        ))

        logger.info(
            "executor.step_done",
            step_id=step.id,
            tool=step.tool_name,
            success=result.success,
            verified=verified,
        )

    async def execute_single_tool(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Execute a single tool directly (bypassing the planner)."""
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(success=False, error=f"Tool '{tool_name}' not found.")

        try:
            result = await tool.execute(**(params or {}))
            verified = await self._verifier.verify_tool_result(tool, result)
            if not verified:
                if not result.metadata:
                    result.metadata = {}
                result.metadata["verification_warning"] = "Output did not pass verification"
                
            if result.success and verified and tool.metadata.dangerous:
                seal_id = TruthSealManager.issue_seal(tool.name, params or {}, result.output)
                if not result.metadata:
                    result.metadata = {}
                result.metadata["truth_seal"] = seal_id
                
            return result
        except Exception as exc:
            return ToolResult(success=False, error=f"Execution failed: {exc}")
