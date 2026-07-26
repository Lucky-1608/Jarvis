from typing import Any
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter
from jarvis.team.sub_agent import SubAgent
from jarvis.router.ai_router import AIRouter


class DelegateTaskTool(Tool):
    """
    Delegate a complex sub-task to a specialized sub-agent.
    """
    
    def __init__(self, router: AIRouter) -> None:
        self._router = router
        
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="delegate_task",
            description="Delegate a complex sub-task to a specialized sub-agent persona.",
            category=ToolCategory.SYSTEM,
            dangerous=False,
            parameters=[
                ToolParameter(
                    name="persona",
                    type="string",
                    description="The description/system prompt for the specialized sub-agent. E.g. 'You are an expert Python security auditor.'"
                ),
                ToolParameter(
                    name="task",
                    type="string",
                    description="The specific task or question for the sub-agent to solve."
                )
            ]
        )

    async def execute(self, **kwargs) -> Any:
        persona = kwargs.get("persona", "You are a helpful AI assistant.")
        task = kwargs.get("task", "")
        
        if not task:
            return "Error: No task provided."
            
        agent = SubAgent(name="DelegatedExpert", persona=persona, router=self._router)
        result = await agent.execute_task(task)
        
        return f"--- Sub-Agent Response ---\n{result}\n--- End Response ---"


def get_team_tools(router: AIRouter) -> list[Tool]:
    """Return all team/delegation tools."""
    return [
        DelegateTaskTool(router)
    ]
