"""
Jarvis OS - Intelligent Tool Selector
Pre-filters available tools based on user intent to save context window tokens
and reduce LLM hallucinations.
"""
from __future__ import annotations

import json
from typing import Any
import structlog
from jarvis.providers.base import Message
from jarvis.router.ai_router import AIRouter
from jarvis.tools.registry import ToolRegistry

logger = structlog.get_logger(__name__)

class ToolSelector:
    def __init__(self, router: AIRouter, registry: ToolRegistry) -> None:
        self._router = router
        self._registry = registry

    async def select_tools(self, user_input: str) -> list[str]:
        """
        Use a lightweight LLM request to classify which tools are needed.
        Returns a list of tool names.
        """
        # Build tool catalog text
        tools = self._registry.list_all()
        catalog_lines = []
        for t in tools:
            catalog_lines.append(f"- {t.name}: {t.description}")
        catalog = "\n".join(catalog_lines)

        system_prompt = (
            "You are an expert intent analyzer for an autonomous AI assistant.\n"
            "Your job is to read the user's prompt and output a JSON array of tool names "
            "that might be required to fulfill the user's request. Be generous but filter out obviously unrelated tools.\n"
            "Only output valid JSON in this format: {\"tools\": [\"tool_name1\", \"tool_name2\"]}\n\n"
            "AVAILABLE TOOLS:\n"
            f"{catalog}\n\n"
            "Always include 'search_web' or general OS tools if the request implies generic reasoning or lookup."
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_input),
        ]

        try:
            # We want a fast, cheap model if possible, but we'll use the primary router for now
            # since it already handles fallback and latency.
            # We enforce JSON output format if supported.
            response = await self._router.chat(
                messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            
            content = response.content or ""
            # Some providers might wrap json in markdown block
            content = content.replace("```json", "").replace("```", "").strip()
            
            data = json.loads(content)
            selected_tools = data.get("tools", [])
            
            if not isinstance(selected_tools, list):
                selected_tools = []
                
            logger.info("tool_selector.success", input_preview=user_input[:30], selected_count=len(selected_tools))
            return [str(t) for t in selected_tools]
            
        except Exception as e:
            logger.warning("tool_selector.failed", error=str(e))
            # Fallback to returning ALL tools so the pipeline doesn't break
            return self._registry.list_names()
