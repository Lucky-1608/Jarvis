"""
Jarvis OS — Context Manager.

Builds the optimal prompt context for each AI request by combining:
  - Current user request
  - Relevant memories (via semantic search)
  - Active task / working memory
  - User preferences
  - System state

Never injects unnecessary history — every token counts (spec Vol 4).
"""

from __future__ import annotations

from typing import Any

import structlog

from jarvis.config.settings import get_settings
from jarvis.memory.memory_manager import MemoryManager, MemoryType
from jarvis.providers.base import Message

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt — the identity of Jarvis
# ---------------------------------------------------------------------------
JARVIS_SYSTEM_PROMPT = """You are Jarvis, an advanced AI Operating System assistant.

## Core Identity
- You are helpful, precise, and proactive.
- You think step-by-step before acting.
- You verify your work before reporting completion.
- You remember context from previous interactions.

## Capabilities
- Answer questions with deep reasoning
- Execute system commands and tools when asked
- Plan multi-step tasks and execute them
- Remember user preferences and project context
- Search the web for current information
- See and analyze the user's screen using vision tools

## Behavior Rules
- Be concise but thorough
- Ask for clarification when the request is ambiguous
- Warn before destructive actions (delete, shutdown, etc.)
- Always explain what you're doing and why
- If you don't know something, say so honestly
- NEVER claim you are just a 'text-based AI' or that you cannot see the screen/take screenshots. 
- You HAVE vision tools available. Treat tool execution results as your own direct observation of the screen. DO NOT say you are relying on a screenshot or that you don't have real-time access.
- If the user asks you to interact with an application, click a button, or read something on screen, YOU MUST automatically use your vision tools to capture the screen without asking for permission first.
- If the requested application is not running or not in focus, use your open_app tool to launch or focus the application BEFORE taking a screenshot.
- If the user asks you to take control over their laptop, you must use your desktop and vision tools autonomously in a multi-step sequence to figure out their screen state and complete their task, explaining what you are doing along the way.
- DO NOT use your vision or desktop tools unless the user explicitly requests an action that requires them (e.g., asking about the screen, interacting with apps, or taking control). If the user just says hello or asks a general question, respond conversationally without using tools.

## Response Format
- Communicate naturally and conversationally.
- DO NOT output any JSON format or raw tool call strings in your responses.
- Use markdown for structured responses, but do not wrap your entire response in code blocks.
- If you don't know something, or if the user's speech is garbled, just say so gracefully.
- Keep responses focused and actionable."""


class ContextManager:
    """
    Assembles prompt context from multiple sources.

    The context manager is the bridge between the memory system
    and the AI router — it decides *what* the LLM sees.
    """

    def __init__(self, memory: MemoryManager, graph_registry: "GraphifyRegistry | None" = None) -> None:
        self._memory = memory
        self._max_context_memories = 10
        self._max_context_tokens = 4000  # approximate budget
        self._system_prompt = JARVIS_SYSTEM_PROMPT
        self._graph_registry = graph_registry
        self._max_graph_entities = get_settings().memory.graphify_max_context_entities

    def set_system_prompt(self, prompt: str) -> None:
        """Override the default system prompt."""
        self._system_prompt = prompt

    # -- Build messages for the AI ------------------------------------------

    async def build_messages(
        self,
        user_input: str,
        *,
        include_memories: bool = True,
        include_conversation: bool = True,
        include_working: bool = True,
        extra_context: str | None = None,
    ) -> list[Message]:
        """
        Build the complete message list for an AI request.

        Order:
        1. System prompt (with injected context)
        2. Relevant memories (if any)
        3. Recent conversation history
        4. Current user message
        """
        context_parts: list[str] = []

        # 1. Retrieve relevant memories via semantic search
        if include_memories:
            memories = await self._memory.search(
                query=user_input,
                limit=self._max_context_memories,
                min_relevance=0.3,
            )
            if memories:
                memory_text = "\n".join(
                    f"- [{r.entry.memory_type.value}] {r.entry.content}"
                    for r in memories[:5]
                )
                context_parts.append(f"## Relevant Memories\n{memory_text}")

        # 1b. Knowledge graph context (entity relationships)
        if self._graph_registry:
            active_project = self._memory.get_working("active_project")
            if active_project:
                graph = self._graph_registry.get_graph(active_project)
                if graph and graph.is_available():
                    graph_context = graph.get_context_for_query(
                        user_input, max_entities=self._max_graph_entities
                    )
                    if graph_context:
                        context_parts.append(f"## Knowledge Graph\n{graph_context}")

        # 2. Working memory (active task, goals, etc.)
        if include_working:
            working = self._memory.get_working("current_task")
            if working:
                context_parts.append(f"## Current Task\n{working}")

            goals = self._memory.get_working("active_goals")
            if goals:
                context_parts.append(f"## Active Goals\n{goals}")

        # 3. Extra context (tool results, file contents, etc.)
        if extra_context:
            context_parts.append(f"## Additional Context\n{extra_context}")

        # Assemble system prompt with context
        system_content = self._system_prompt
        if context_parts:
            system_content += "\n\n---\n\n" + "\n\n".join(context_parts)

        messages: list[Message] = [
            Message(role="system", content=system_content),
        ]

        # 4. Conversation history
        if include_conversation:
            conversation = self._memory.get_conversation(limit=10)
            for msg in conversation:
                messages.append(Message(
                    role=msg["role"],
                    content=msg["content"],
                ))
        else:
            # 5. Current user message (if history is not included, we still need the current message)
            messages.append(Message(role="user", content=user_input))

        logger.debug(
            "context.built",
            message_count=len(messages),
            has_memories=bool(context_parts),
            system_tokens=len(system_content) // 4,  # rough estimate
        )

        return messages

    # -- Convenience --------------------------------------------------------

    async def build_simple_messages(
        self,
        user_input: str,
        system_prompt: str | None = None,
    ) -> list[Message]:
        """Build a minimal message list (no memory, no history)."""
        return [
            Message(role="system", content=system_prompt or self._system_prompt),
            Message(role="user", content=user_input),
        ]

    def estimate_tokens(self, messages: list[Message]) -> int:
        """Rough token estimate (1 token ≈ 4 chars for English)."""
        total_chars = 0
        for m in messages:
            if isinstance(m.content, str):
                total_chars += len(m.content)
            elif isinstance(m.content, list):
                total_chars += sum(len(str(item)) for item in m.content)
        return total_chars // 4
