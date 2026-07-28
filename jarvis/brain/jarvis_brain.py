"""
Jarvis OS — Brain (Core Orchestrator).

The central nervous system that ties every module together.

Execution Flow (spec Volume 1):
  Input → Intent Analysis → Router → Planner → Executor →
  Verification → Memory Update → Response

The Brain is the ONLY entry point for user requests.
All other modules are internal.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import structlog

from jarvis.config.settings import get_settings
from jarvis.events.bus import Event, EventTypes, get_event_bus
from jarvis.executor.executor import Executor
from jarvis.memory.context_manager import ContextManager
from jarvis.memory.memory_manager import MemoryManager, MemoryType
from jarvis.planner.planner import Planner
from jarvis.providers.base import Message, StreamChunk
from jarvis.router.ai_router import AIRouter
from jarvis.tools.builtin.system_tools import get_system_tools
from jarvis.tools.builtin.web_tools import get_web_tools
from jarvis.vision.vision_tools import get_vision_tools
from jarvis.automation.browser.tools import get_browser_tools
from jarvis.automation.desktop.tools import get_desktop_tools
from jarvis.tools.registry import ToolRegistry
from jarvis.verification.verifier import Verifier

logger = structlog.get_logger(__name__)


@dataclass
class JarvisResponse:
    """Complete response from Jarvis for a user request."""

    content: str
    plan: dict[str, Any] | None = None
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    memories_used: int = 0


class JarvisBrain:
    """
    The brain of Jarvis OS.

    Orchestrates:
    - AI Router (model selection)
    - Memory Manager (context & persistence)
    - Context Manager (prompt assembly)
    - Planner (task decomposition)
    - Executor (tool calling)
    - Verifier (result checking)
    - Event Bus (inter-module communication)

    Usage::

        brain = JarvisBrain()
        await brain.initialize()
        response = await brain.process("What's the weather?")
        print(response.content)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._bus = get_event_bus()

        # Core modules — initialized in ``initialize()``
        self._router: AIRouter | None = None
        self._memory: MemoryManager | None = None
        self._context: ContextManager | None = None
        self._tools: ToolRegistry | None = None
        self._planner: Planner | None = None
        self._executor: Executor | None = None
        self._verifier: Verifier | None = None

        self._agent_history: list[dict] = []
        self._workflow_history: list[dict] = []

        self._initialized = False

    # -- Lifecycle ----------------------------------------------------------

    async def initialize(self) -> None:
        """Boot all subsystems."""
        if self._initialized:
            return

        logger.info("brain.initializing")
        start = time.perf_counter()

        # 1. AI Router
        self._router = AIRouter()

        # 2. Memory
        self._memory = MemoryManager()
        self._context = ContextManager(self._memory)

        # 3. Tools
        self._tools = ToolRegistry()
        self._tools.register_many(get_system_tools())
        self._tools.register_many(get_web_tools())
        self._tools.register_many(get_vision_tools())
        self._tools.register_many(get_browser_tools())
        self._tools.register_many(get_desktop_tools())
        from jarvis.tools.builtin.team_tools import get_team_tools
        self._tools.register_many(get_team_tools(self._router))
        from jarvis.tools.builtin.n8n_tools import get_n8n_tools
        self._tools.register_many(get_n8n_tools())

        # 3.5 Plugins
        from jarvis.plugins.manager import PluginManager
        self._plugin_manager = PluginManager(self._tools, self._bus)
        self._plugin_manager.load_all()

        # 4. Verification
        self._verifier = Verifier()

        # 5. Planner & Executor
        self._planner = Planner(self._router, self._tools)
        self._executor = Executor(self._tools, self._verifier)

        self._initialized = True
        elapsed = (time.perf_counter() - start) * 1000

        await self._bus.publish(Event(
            type=EventTypes.SYSTEM_READY,
            data={
                "tools_registered": self._tools.count,
                "boot_time_ms": round(elapsed, 1),
            },
            source="brain",
        ))

        logger.info(
            "brain.ready",
            tools=self._tools.count,
            primary_provider=self._settings.ai_primary_provider,
            boot_ms=round(elapsed, 1),
        )

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("brain.shutting_down")
        await self._bus.publish(Event(
            type=EventTypes.SYSTEM_SHUTDOWN,
            source="brain",
        ))
        self._initialized = False

    # -- Main Processing Pipeline -------------------------------------------

    async def process(self, user_input: str) -> JarvisResponse:
        """
        Process a user request through the full pipeline.

        This is the main entry point for all user interactions.

        Flow:
        1. Record input in conversation buffer
        2. Build context (memories + conversation + system prompt)
        3. Create execution plan (if multi-step)
        4. Execute plan steps (tools)
        5. Generate final AI response
        6. Store in memory
        7. Return response
        """
        if not self._initialized:
            await self.initialize()

        start = time.perf_counter()

        # 1. Add to conversation buffer
        self._memory.add_to_conversation("user", user_input)


        # 2. Build context
        messages = await self._context.build_messages(user_input)

        # 3. Get AI response with tools (multi-step loop)
        openai_tools = self._tools.to_openai_tools() if self._tools and self._tools.count > 0 else None
        
        MAX_STEPS = 5
        tool_results: list[dict[str, Any]] = []
        plan_dict = None
        
        from jarvis.providers.base import Message

        for step_idx in range(MAX_STEPS):
            ai_response = await self._router.chat(messages, tools=openai_tools)
            
            if not ai_response.tool_calls:
                # If the model emits a generic tool-calling fallback message, 
                # re-run the chat without tools so it answers conversationally.
                if ai_response.content and "I don't have a specific function to call" in ai_response.content:
                    ai_response = await self._router.chat(messages)
                break
                
            messages.append(Message(
                role="assistant",
                content=ai_response.content or "",
                tool_calls=ai_response.tool_calls
            ))

            from jarvis.planner.planner import ExecutionPlan, PlanStep
            import json
            import time as _time

            steps = []
            requires_confirmation = False
            for i, tc in enumerate(ai_response.tool_calls):
                func = tc.get("function", {})
                tool_name = func.get("name")
                
                tool = self._tools.get(tool_name)
                if tool and tool.is_dangerous:
                    requires_confirmation = True

                try:
                    params = json.loads(func.get("arguments", "{}"))
                except json.JSONDecodeError:
                    params = {}

                steps.append(PlanStep(
                    id=i,
                    description=f"Run {tool_name}",
                    tool_name=tool_name,
                    tool_params=params,
                    tool_call_id=tc.get("id"),
                    depends_on=[],
                ))

            plan = ExecutionPlan(
                goal=user_input,
                steps=steps,
                requires_confirmation=requires_confirmation,
                reasoning=f"Determined via native tool calling (step {step_idx + 1})",
            )
            
            workflow_entry = {
                "id": f"plan_{int(_time.time())}",
                "goal": user_input,
                "status": "running",
                "requires_confirmation": plan.requires_confirmation,
                "reasoning": plan.reasoning,
                "timestamp": _time.time(),
                "steps": [{
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool_name,
                    "status": s.status.value,
                } for s in plan.steps],
            }
            self._workflow_history.insert(0, workflow_entry)

            executed_plan = await self._executor.execute_plan(plan)
            for step in executed_plan.steps:
                tool_results.append({
                    "step": step.id,
                    "tool": step.tool_name,
                    "description": step.description,
                    "status": step.status.value,
                    "result": step.result,
                    "error": step.error,
                })
                
                result_str = str(step.result) if step.status.value == "completed" else str(step.error)
                messages.append(Message(
                    role="tool",
                    content=result_str,
                    name=step.tool_name,
                    tool_call_id=step.tool_call_id
                ))

            if self._workflow_history:
                wf = self._workflow_history[0]
                wf["status"] = "failed" if plan.has_failures else "completed"
                wf["steps"] = [{
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool_name,
                    "status": s.status.value,
                } for s in plan.steps]

            plan_dict = plan.to_dict()

        # 5. Verify AI response
        verification = await self._verifier.verify_ai_response(ai_response.content)
        if not verification["valid"]:
            logger.warning("brain.response_verification_issues", issues=verification["issues"])

        # 6. Store in memory
        self._memory.add_to_conversation("assistant", ai_response.content)

        # Store significant interactions in long-term memory
        if len(user_input) > 20:  # Skip trivial inputs
            try:
                await self._memory.store(
                    content=f"User: {user_input}\nJarvis: {ai_response.content[:500]}",
                    memory_type=MemoryType.CONVERSATION,
                    metadata={"type": "interaction"},
                    importance=0.3,
                    chunk=False,
                )
            except Exception as exc:
                logger.warning("brain.memory_store_failed", error=str(exc))

        elapsed = (time.perf_counter() - start) * 1000

        response = JarvisResponse(
            content=ai_response.content,
            plan=plan_dict,
            tool_results=tool_results,
            provider=ai_response.provider,
            model=ai_response.model,
            latency_ms=elapsed,
        )

        logger.info(
            "brain.processed",
            input_preview=user_input[:60],
            provider=ai_response.provider,
            model=ai_response.model,
            tools_used=len(tool_results),
            latency_ms=round(elapsed, 1),
        )

        return response

    # -- Streaming ----------------------------------------------------------

    async def process_stream(self, user_input: str) -> AsyncIterator[StreamChunk]:
        """
        Stream a response token-by-token.

        Simplified flow (no planning) — used for real-time chat UI.
        """
        if not self._initialized:
            await self.initialize()

        direct_plan = self._create_direct_control_plan(user_input)
        if direct_plan is not None:
            response = await self.process(user_input)
            yield StreamChunk(
                content=response.content,
                done=True,
                provider=response.provider,
                model=response.model,
            )
            return

        self._memory.add_to_conversation("user", user_input)

        messages = await self._context.build_messages(user_input)

        full_response = ""
        async for chunk in self._router.chat_stream(messages):
            full_response += chunk.content
            yield chunk

        # Store in memory after stream completes
        if full_response:
            self._memory.add_to_conversation("assistant", full_response)

    # -- Convenience accessors -----------------------------------------------

    @property
    def memory(self) -> MemoryManager:
        return self._memory

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    def _create_direct_control_plan(self, user_input: str):
        """Create deterministic plans for obvious PC-control commands."""
        from jarvis.planner.planner import ExecutionPlan, PlanStep

        text = " ".join(user_input.strip().split())
        lower = text.lower()
        lower = re.sub(r"^\s*(jarvis|hey jarvis|ok jarvis|okay jarvis)[,\s]+", "", lower)

        def plan(tool_name: str, params: dict[str, Any], description: str) -> ExecutionPlan:
            return ExecutionPlan(
                goal=user_input,
                reasoning="Direct desktop-control intent detected.",
                requires_confirmation=False,
                steps=[
                    PlanStep(
                        id=0,
                        description=description,
                        tool_name=tool_name,
                        tool_params=params,
                        depends_on=[],
                    )
                ],
            )

        quoted = self._extract_quoted_text(text)



        if any(phrase in lower for phrase in ("take screenshot", "capture screenshot", "screenshot")):
            return plan(
                "take_screenshot",
                {"target": "full_screen"},
                "Capture the screen.",
            )

        if any(phrase in lower for phrase in ("what is on my screen", "what's on my screen", "see my screen", "analyze screen", "look at screen")):
            return plan(
                "analyze_screen",
                {"query": "Describe the current screen and visible application state."},
                "Analyze the screen.",
            )

        open_match = re.search(r"\b(open|launch|start)\s+(.+)$", lower)
        if open_match:
            app_name = self._clean_app_target(open_match.group(2))
            if app_name:
                return plan("open_app", {"app_name": app_name}, f"Open {app_name}.")

        close_match = re.search(r"\b(close|quit|exit|terminate|kill|stop)\s+(.+)$", lower)
        if close_match:
            app_name = self._clean_app_target(close_match.group(2)) or "current"
            return plan("close_app", {"app_name": app_name}, f"Close {app_name}.")

        if re.fullmatch(r"(close|quit|exit|terminate|kill|stop)(\s+(it|this|app|window))?", lower):
            return plan("close_app", {"app_name": "current"}, "Close the active app.")

        if lower.startswith(("click", "left click", "right click", "double click")):
            coords = self._extract_coordinates(lower)
            button = "right" if "right click" in lower else "left"
            clicks = 2 if "double click" in lower else 1
            params: dict[str, Any] = {"button": button, "clicks": clicks}
            if coords:
                params.update({"x": coords[0], "y": coords[1]})
            return plan("desktop_mouse_click", params, "Click the mouse.")

        move_match = re.search(r"\bmove\s+(?:the\s+)?mouse(?:\s+to)?\s+(.+)$", lower)
        if move_match:
            coords = self._extract_coordinates(move_match.group(1))
            if coords:
                return plan(
                    "desktop_mouse_move",
                    {"x": coords[0], "y": coords[1]},
                    f"Move mouse to {coords[0]}, {coords[1]}.",
                )

        type_match = re.search(r"\b(type|write|enter|input)\s+(.+)$", text, re.IGNORECASE)
        if type_match:
            content = quoted or self._strip_polite_suffix(type_match.group(2))
            if content:
                return plan("desktop_keyboard_type", {"text": content}, "Type text.")

        hotkey_match = re.search(r"\b(press|hit|use)\s+(.+)$", lower)
        if hotkey_match:
            keys = self._parse_hotkey(hotkey_match.group(2))
            if keys:
                return plan("desktop_keyboard_hotkey", {"keys": keys}, f"Press {keys}.")

        if any(phrase in lower for phrase in ("list windows", "show windows", "open windows")):
            return plan(
                "desktop_window_manager",
                {"action": "list_all"},
                "List open windows.",
            )

        if any(phrase in lower for phrase in ("active window", "current window", "foreground window")):
            return plan(
                "desktop_window_manager",
                {"action": "get_active"},
                "Get the active window.",
            )

        focus_match = re.search(r"\b(focus|switch to|activate)\s+(.+)$", lower)
        if focus_match:
            title = self._clean_app_target(focus_match.group(2))
            if title:
                return plan(
                    "desktop_window_manager",
                    {"action": "activate", "title": title},
                    f"Activate {title}.",
                )

        return None

    async def _execute_direct_plan(
        self,
        user_input: str,
        plan,
        start: float,
    ) -> JarvisResponse:
        import time as _time

        workflow_entry = {
            "id": f"plan_{int(_time.time())}",
            "goal": user_input,
            "status": "running",
            "requires_confirmation": plan.requires_confirmation,
            "reasoning": plan.reasoning,
            "timestamp": _time.time(),
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool_name,
                    "status": s.status.value,
                }
                for s in plan.steps
            ],
        }
        self._workflow_history.insert(0, workflow_entry)

        executed_plan = await self._executor.execute_plan(plan)
        tool_results = [
            {
                "step": step.id,
                "tool": step.tool_name,
                "description": step.description,
                "status": step.status.value,
                "result": step.result,
                "error": step.error,
            }
            for step in executed_plan.steps
        ]

        workflow_entry["status"] = "failed" if executed_plan.has_failures else "completed"
        workflow_entry["steps"] = [
            {
                "id": s.id,
                "description": s.description,
                "tool": s.tool_name,
                "status": s.status.value,
            }
            for s in executed_plan.steps
        ]

        content = self._summarize_tool_results(tool_results)
        self._memory.add_to_conversation("assistant", content)

        elapsed = (time.perf_counter() - start) * 1000
        response = JarvisResponse(
            content=content,
            plan=executed_plan.to_dict(),
            tool_results=tool_results,
            provider="local",
            model="direct-control",
            latency_ms=elapsed,
        )

        logger.info(
            "brain.direct_control_processed",
            input_preview=user_input[:60],
            tools_used=len(tool_results),
            latency_ms=round(elapsed, 1),
        )
        return response

    @staticmethod
    def _summarize_tool_results(tool_results: list[dict[str, Any]]) -> str:
        if not tool_results:
            return "I did not find a desktop action to run."

        failures = [r for r in tool_results if r.get("status") == "failed"]
        if failures:
            error = failures[0].get("error") or "The desktop action failed."
            return f"I couldn't complete that PC action: {error}"

        result = tool_results[-1].get("result")
        if result is None:
            return "Done."
        return f"Done. {result}"

    @staticmethod
    def _extract_quoted_text(text: str) -> str:
        match = re.search(r'"([^"]+)"|\'([^\']+)\'', text)
        return (match.group(1) or match.group(2)).strip() if match else ""

    @staticmethod
    def _extract_coordinates(text: str) -> tuple[int, int] | None:
        match = re.search(r"(-?\d{1,5})\D+(-?\d{1,5})", text)
        if not match:
            return None
        return int(match.group(1)), int(match.group(2))

    @staticmethod
    def _clean_app_target(target: str) -> str:
        cleaned = re.sub(r"\b(please|now|for me|on my pc|in my pc|on pc|in pc)\b", "", target, flags=re.IGNORECASE)
        cleaned = re.sub(r"^(the|my|a|an)\s+", "", cleaned.strip(), flags=re.IGNORECASE)
        return " ".join(cleaned.strip(" .,!?:;").split())

    @staticmethod
    def _strip_polite_suffix(text: str) -> str:
        cleaned = re.sub(r"\b(please|for me|now)\b", "", text, flags=re.IGNORECASE)
        return cleaned.strip(" .,!?:;")

    @staticmethod
    def _parse_hotkey(text: str) -> str:
        cleaned = text.strip(" .,!?:;").lower()
        replacements = {
            "control": "ctrl",
            "command": "cmd",
            "escape": "esc",
            "delete": "del",
            "plus": "+",
        }
        for old, new in replacements.items():
            cleaned = re.sub(rf"\b{old}\b", new, cleaned)

        cleaned = cleaned.replace(" and ", "+").replace(",", "+").replace(" ", "+")
        parts = [p for p in cleaned.split("+") if p and p not in {"key", "keys"}]
        if not parts:
            return ""
        return ",".join(parts)

    @property
    def router(self) -> AIRouter:
        return self._router

    @property
    def agent_history(self) -> list[dict]:
        return self._agent_history

    @property
    def workflow_history(self) -> list[dict]:
        return self._workflow_history

    async def get_health(self) -> dict[str, Any]:
        """Return health status of all subsystems."""
        provider_health = await self._router.health_check() if self._router else {}
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "initialized": self._initialized,
            "tools_registered": self._tools.count if self._tools else 0,
            "memory_stats": self._memory.get_stats() if self._memory else {},
            "providers": {
                name: {
                    "available": h.available,
                    "latency_ms": round(h.latency_ms, 1),
                    "error": h.error,
                }
                for name, h in provider_health.items()
            },
            "router_metrics": self._router.get_metrics() if self._router else {},
        }
