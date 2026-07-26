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

        # 2. Create execution plan
        plan = await self._planner.create_plan(user_input)

        tool_results: list[dict[str, Any]] = []

        # 3. Execute plan if there are tool steps
        if plan.steps:
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

        # 4. Build context and generate response
        extra_context = None
        if tool_results:
            # Inject tool results into the context
            results_text = "\n".join(
                f"Tool '{r['tool']}': {r['status']} — {str(r.get('result', ''))[:500]}"
                for r in tool_results
            )
            extra_context = (
                f"## Tool Execution Results\n{results_text}\n\n"
                f"**CRITICAL INSTRUCTION:** The tools have already been executed. "
                f"Acknowledge the success or failure to the user in a short, conversational sentence. "
                f"Do NOT output any JSON, tool calls, or markdown code blocks in your response."
            )

        messages = await self._context.build_messages(
            user_input,
            extra_context=extra_context,
        )

        # 5. Get AI response
        ai_response = await self._router.chat(messages)

        # 6. Verify AI response
        verification = await self._verifier.verify_ai_response(ai_response.content)
        if not verification["valid"]:
            logger.warning("brain.response_verification_issues", issues=verification["issues"])

        # 7. Store in memory
        self._memory.add_to_conversation("assistant", ai_response.content)

        # Store significant interactions in long-term memory
        if len(user_input) > 20:  # Skip trivial inputs
            await self._memory.store(
                content=f"User: {user_input}\nJarvis: {ai_response.content[:500]}",
                memory_type=MemoryType.CONVERSATION,
                metadata={"type": "interaction"},
                importance=0.3,
                chunk=False,
            )

        elapsed = (time.perf_counter() - start) * 1000

        response = JarvisResponse(
            content=ai_response.content,
            plan=plan.to_dict() if plan.steps else None,
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

    @property
    def router(self) -> AIRouter:
        return self._router

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
