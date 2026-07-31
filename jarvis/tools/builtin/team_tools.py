from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter
from jarvis.team.sub_agent import SubAgent
from jarvis.router.ai_router import AIRouter
import time

# Module-level agent history for tracking spawned agents
_agent_history: list[dict] = []

def get_agent_history() -> list[dict]:
    return _agent_history


class DelegateTaskTool(Tool):
    """Delegate a complex sub-task to a specialized sub-agent."""
    
    def __init__(self, router: AIRouter) -> None:
        self._router = router
        
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="delegate_task",
            description="Delegate a complex sub-task to a specialized sub-agent. You can specify a registered agent name, or a custom persona.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="agent_name",
                    type="string",
                    description="The name of the explicitly registered agent (e.g. 'Database Agent', 'Frontend Agent')."
                ),
                ToolParameter(
                    name="persona",
                    type="string",
                    description="Optional. A custom system prompt/persona if not using a registered agent."
                ),
                ToolParameter(
                    name="task",
                    type="string",
                    description="The specific task or question for the sub-agent to solve."
                )
            ]
        )

    async def execute(self, **kwargs) -> Any:
        agent_name = kwargs.get("agent_name")
        persona = kwargs.get("persona", "You are a helpful AI assistant.")
        task = kwargs.get("task", "")
        
        if not task:
            return "Error: No task provided."
            
        from jarvis.team.registry import team_registry
        
        agent = None
        if agent_name:
            agent_class = team_registry.get_agent(agent_name)
            if agent_class:
                agent = agent_class(router=self._router)
        
        if not agent:
            # Fallback to dynamic agent
            actual_name = agent_name or "DelegatedExpert"
            agent = SubAgent(name=actual_name, persona=persona, router=self._router)
        
        # Track agent in history
        agent_entry = {
            "id": f"agent_{int(time.time())}_{len(_agent_history)}",
            "name": agent.name,
            "type": "SubAgent",
            "persona": agent.persona[:200],
            "status": "running",
            "created_at": time.time(),
            "task": task[:200],
        }
        _agent_history.insert(0, agent_entry)
        
        result = await agent.execute_task(task)
        
        # Update status
        agent_entry["status"] = "completed"
        agent_entry["completed_at"] = time.time()
        
        return f"--- Sub-Agent Response ---\n{result}\n--- End Response ---"


def get_team_tools(router: AIRouter) -> list[Tool]:
    return [DelegateTaskTool(router)]
