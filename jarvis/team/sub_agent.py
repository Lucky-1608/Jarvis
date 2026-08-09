"""
Jarvis OS - Sub Agent

A simplified wrapper around the AI Router that allows Jarvis to spawn
specialized personas to solve complex sub-tasks.
"""

import structlog

from jarvis.providers.base import Message
from jarvis.router.ai_router import AIRouter
from jarvis.tools.base import Tool

logger = structlog.get_logger(__name__)


class SubAgent:
    """
    An isolated agent with a specific persona and toolset.
    """

    name = "BaseSubAgent" # To be overridden by explicit agents
    persona = "You are a helpful assistant."

    def __init__(self, name: str | None = None, persona: str | None = None, router: AIRouter = None, tools: list[Tool] | None = None) -> None:
        self.name = name or self.name
        self.persona = persona or self.persona
        self._router = router
        self._tools = tools or []

    async def execute_task(self, task: str) -> str:
        """Execute a single task and return the response."""
        logger.info("sub_agent.execute_task", agent=self.name, task_length=len(task), tools_count=len(self._tools))

        messages = [
            Message(role="system", content=f"You are a specialized agent named {self.name}.\n{self.persona}"),
            Message(role="user", content=task)
        ]

        # Convert Jarvis Tools to OpenAI format if provided
        openai_tools = None
        if self._tools:
            openai_tools = []
            for t in self._tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.metadata.name,
                        "description": t.metadata.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                p.name: {"type": p.type, "description": p.description}
                                for p in t.metadata.parameters
                            },
                            "required": [p.name for p in t.metadata.parameters if p.required]
                        }
                    }
                })

        try:
            # Note: We need a loop here if the sub_agent actually executes tools,
            # but for now we'll just pass them to the router. To fully implement
            # tool execution within sub_agents, we'd need an executor loop like in JarvisBrain.
            # We'll just let the router use them. (Simplification for now).
            response = await self._router.chat(messages, tools=openai_tools)
            logger.info("sub_agent.task_complete", agent=self.name)
            return response.content
        except Exception as e:
            logger.error("sub_agent.task_failed", agent=self.name, error=str(e))
            return f"Agent {self.name} failed: {str(e)}"
