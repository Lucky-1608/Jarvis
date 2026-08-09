"""
Jarvis OS - Team Registry

Manages explicitly defined agent personas in the team roster.
"""


import structlog

from jarvis.team.sub_agent import SubAgent

logger = structlog.get_logger(__name__)

class TeamRegistry:
    """Registry for explicitly defined agent classes."""

    def __init__(self):
        self._agents: dict[str, type[SubAgent]] = {}

    def register(self, agent_class: type[SubAgent]) -> None:
        """Register a new specialized agent."""
        if not hasattr(agent_class, "name"):
            logger.warning("team_registry.missing_name", agent_class=agent_class.__name__)
            return

        name = getattr(agent_class, "name")
        self._agents[name] = agent_class
        logger.info("team_registry.registered", agent=name)

    def get_agent(self, name: str) -> type[SubAgent] | None:
        """Retrieve an agent class by name."""
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """List all available agents in the registry."""
        return list(self._agents.keys())

# Global registry instance
team_registry = TeamRegistry()
