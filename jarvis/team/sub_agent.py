"""
Jarvis OS - Sub Agent

A simplified wrapper around the AI Router that allows Jarvis to spawn
specialized personas to solve complex sub-tasks.
"""

from typing import Any
import structlog
from jarvis.router.ai_router import AIRouter
from jarvis.providers.base import Message

logger = structlog.get_logger(__name__)


class SubAgent:
    """
    An isolated agent with a specific persona.
    """

    def __init__(self, name: str, persona: str, router: AIRouter) -> None:
        self.name = name
        self.persona = persona
        self._router = router

    async def execute_task(self, task: str) -> str:
        """Execute a single task and return the response."""
        logger.info("sub_agent.execute_task", agent=self.name, task_length=len(task))
        
        messages = [
            Message(role="system", content=f"You are a specialized agent named {self.name}.\n{self.persona}"),
            Message(role="user", content=task)
        ]
        
        try:
            response = await self._router.chat(messages)
            logger.info("sub_agent.task_complete", agent=self.name)
            return response.content
        except Exception as e:
            logger.error("sub_agent.task_failed", agent=self.name, error=str(e))
            return f"Agent {self.name} failed: {str(e)}"
