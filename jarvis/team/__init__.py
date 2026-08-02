"""
Jarvis OS - Team Sub-Agents
"""
from .registry import team_registry

# Import Core Agents
from .core import (
    CodingAgent,
    ResearchAgent,
    ArchitectureAgent,
    DevOpsAgent,
    SecurityAgent
)

# Import Specialist Agents
from .specialists import (
    FrontendAgent,
    DatabaseAgent,
    UiUxAgent,
    BackendAgent,
    ApiAgent,
    AnalyticsAgent,
    DocumentationAgent,
    WritingAgent,
    MultimediaAgent,
    ProductivityAgent,
    FinanceAgent,
    BrowserAgent,
    InventoryAgent,
    LearningAgent,
    KnowledgeAgent,
    PluginAgent,
    MaintenanceAgent
)

# Register Core Agents
team_registry.register(CodingAgent)
team_registry.register(ResearchAgent)
team_registry.register(ArchitectureAgent)
team_registry.register(DevOpsAgent)
team_registry.register(SecurityAgent)

# Register Specialist Agents
team_registry.register(FrontendAgent)
team_registry.register(DatabaseAgent)

# Register Auto-generated Specialists
team_registry.register(UiUxAgent)
team_registry.register(BackendAgent)
team_registry.register(ApiAgent)
team_registry.register(AnalyticsAgent)
team_registry.register(DocumentationAgent)
team_registry.register(WritingAgent)
team_registry.register(MultimediaAgent)
team_registry.register(ProductivityAgent)
team_registry.register(FinanceAgent)
team_registry.register(BrowserAgent)
team_registry.register(InventoryAgent)
team_registry.register(LearningAgent)
team_registry.register(KnowledgeAgent)
team_registry.register(PluginAgent)
team_registry.register(MaintenanceAgent)
