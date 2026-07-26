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

## Behavior Rules
- Be concise but thorough
- Ask for clarification when the request is ambiguous
- Warn before destructive actions (delete, shutdown, etc.)
- Always explain what you're doing and why
- If you don't know something, say so honestly

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

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory
        self._max_context_memories = 10
        self._max_context_tokens = 4000  # approximate budget
        self._system_prompt = JARVIS_SYSTEM_PROMPT

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

        # 5. Current user message
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
        total_chars = sum(len(m.content) for m in messages)
        return total_chars // 4
