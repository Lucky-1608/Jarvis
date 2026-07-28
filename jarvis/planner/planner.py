"""
Jarvis OS — Planning Engine.

Breaks complex user requests into structured, executable plans.

Flow (spec Volume 1):
  User Intent → Planner → Execution Plan → Executor

The Planner uses the LLM to decompose goals into ordered steps,
each assigned to a specific tool. Simple requests skip planning
entirely and go straight to the AI or a single tool.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.providers.base import Message
from jarvis.router.ai_router import AIRouter
from jarvis.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Plan data structures
# ---------------------------------------------------------------------------
class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """A single step in an execution plan."""

    id: int
    description: str
    tool_name: str | None = None  # None means "ask the AI"
    tool_params: dict[str, Any] = field(default_factory=dict)
    tool_call_id: str | None = None
    depends_on: list[int] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str | None = None


@dataclass
class ExecutionPlan:
    """A structured plan with ordered steps."""

    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    requires_confirmation: bool = False
    reasoning: str = ""

    @property
    def is_complete(self) -> bool:
        return all(s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED) for s in self.steps)

    @property
    def has_failures(self) -> bool:
        return any(s.status == StepStatus.FAILED for s in self.steps)

    @property
    def next_step(self) -> PlanStep | None:
        for step in self.steps:
            if step.status == StepStatus.PENDING:
                # Check all dependencies are completed
                deps_met = all(
                    self.steps[d].status == StepStatus.COMPLETED
                    for d in step.depends_on
                    if d < len(self.steps)
                )
                if deps_met:
                    return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "reasoning": self.reasoning,
            "requires_confirmation": self.requires_confirmation,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool_name,
                    "params": s.tool_params,
                    "depends_on": s.depends_on,
                    "status": s.status.value,
                }
                for s in self.steps
            ],
        }


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

PLANNING_PROMPT = """You are the planning engine of Jarvis OS. Analyze the user's request and create an execution plan.
You MUST output ONLY valid JSON. NEVER reply with conversational text.

## Available Tools
{tools_description}

## Instructions
1. Break the user's request into clear, ordered steps.
2. Assign each step to a tool from the list. If the user asks to "open", "run", "search", "navigate", or perform an action, you MUST use a tool. Do NOT just reply with a URL or text.
3. If the user asks to open a website in their default browser, Edge, or Chrome, use the 'open_app' tool with the URL as the app_name. Do NOT use browser_navigate unless they specifically want Jarvis to automate/read the page.
4. If the user asks to close, quit, exit, stop, kill, or terminate an app/window, you MUST use the 'close_app' tool. For vague requests like "close this app", "close current app", or "close the app", set app_name to "current".
5. If the user asks about their screen, what they are looking at, "what is this", "what's this", or asks to take a screenshot, you MUST use the `analyze_screen` or `take_screenshot` tool to get visual context.
6. Identify dependencies between steps.
7. Flag if any step requires user confirmation (dangerous operations).

## Response Format
Respond with ONLY valid JSON matching this exact structure:
```json
{{
  "reasoning": "Brief explanation of your plan",
  "requires_confirmation": false,
  "steps": [
    {{
      "id": 0,
      "description": "What this step does",
      "tool": "tool_name",
      "params": {{"param_name": "param_value"}},
      "depends_on": []
    }}
  ]
}}
```

If the request is purely a conversational question that requires NO action and NO tools, respond with:
```json
{{
  "reasoning": "Simple question — no tools needed",
  "requires_confirmation": false,
  "steps": []
}}
```"""


class Planner:
    """
    Creates structured execution plans from user requests.

    For simple queries (questions, chat), returns an empty plan
    so the Brain can handle them directly with the LLM.
    For complex multi-step tasks, decomposes them into tool calls.
    """

    def __init__(self, router: AIRouter, tool_registry: ToolRegistry) -> None:
        self._router = router
        self._tools = tool_registry
        self._bus = get_event_bus()

    async def create_plan(self, user_input: str) -> ExecutionPlan:
        """
        Analyze *user_input* and produce an ``ExecutionPlan``.

        Simple questions return an empty plan (no tool steps).
        Complex requests are decomposed into tool-calling steps.
        """
        # Build tool descriptions for the prompt
        tools_desc = "\n".join(
            f"- **{m.name}**: {m.description} (params: {', '.join(p.name for p in m.parameters)})"
            for m in self._tools.list_all()
        ) or "No tools registered."

        system_prompt = PLANNING_PROMPT.format(tools_description=tools_desc)

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_input),
        ]

        try:
            response = await self._router.chat(
                messages,
                temperature=0.2,  # low temp for structured output
                max_tokens=2048,
                response_format={"type": "json_object"},
            )

            content = response.content.strip()
            
            # Extract JSON from markdown block or outermost braces
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                brace_match = re.search(r"(\{.*\})", content, re.DOTALL)
                if brace_match:
                    content = brace_match.group(1)
            
            plan_data = json.loads(content)
            plan = self._parse_plan(user_input, plan_data)

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("planner.parse_error", error=str(exc))
            # Fall back to an empty plan (let the Brain answer directly)
            plan = ExecutionPlan(
                goal=user_input,
                reasoning="Could not generate a structured plan; will answer directly.",
            )

        await self._bus.publish(Event(
            type=EventTypes.PLAN_CREATED,
            data=plan.to_dict(),
            source="planner",
        ))

        logger.info(
            "planner.plan_created",
            goal=user_input[:80],
            steps=len(plan.steps),
            requires_confirmation=plan.requires_confirmation,
        )
        return plan

    def _parse_plan(self, goal: str, data: dict[str, Any]) -> ExecutionPlan:
        """Parse the LLM JSON response into an ``ExecutionPlan``."""
        steps = []
        
        # Handle simplified {"tool": "name", "args": {...}} format from weaker models
        if "tool" in data and ("args" in data or "params" in data or "arguments" in data) and "steps" not in data:
            tool_name = data["tool"]
            params = data.get("args", data.get("params", data.get("arguments", {})))
            if tool_name and tool_name in self._tools:
                steps.append(PlanStep(
                    id=0,
                    description=f"Run {tool_name}",
                    tool_name=tool_name,
                    tool_params=params,
                    depends_on=[],
                ))
            else:
                logger.warning("planner.unknown_tool", tool=tool_name)
        else:
            # Standard complex format
            for step_data in data.get("steps", []):
                tool_name = step_data.get("tool")
                if tool_name == "null" or tool_name is None:
                    tool_name = None
    
                # Validate tool exists
                if tool_name and tool_name not in self._tools:
                    logger.warning("planner.unknown_tool", tool=tool_name)
                    tool_name = None  # fall back to AI response
    
                steps.append(PlanStep(
                    id=step_data.get("id", len(steps)),
                    description=step_data.get("description", ""),
                    tool_name=tool_name,
                    tool_params=step_data.get("params", step_data.get("args", {})),
                    depends_on=step_data.get("depends_on", []),
                ))

        # Check if any step uses a dangerous tool
        requires_confirmation = data.get("requires_confirmation", False)
        if not requires_confirmation:
            for step in steps:
                if step.tool_name:
                    tool = self._tools.get(step.tool_name)
                    if tool and tool.is_dangerous:
                        requires_confirmation = True
                        break

        return ExecutionPlan(
            goal=goal,
            steps=steps,
            requires_confirmation=requires_confirmation,
            reasoning=data.get("reasoning", ""),
        )
