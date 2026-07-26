"""
Jarvis OS — Tool Base Class.

Every capability in Jarvis is exposed as a Tool (spec Volume 3).
Each tool has:
  - metadata (name, description, parameters schema, category)
  - execute()  — run the tool
  - verify()   — check the result is correct
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolCategory(str, Enum):
    """Categories for organising tools."""

    SYSTEM = "system"
    FILE = "file"
    WEB = "web"
    CODE = "code"
    BROWSER = "browser"
    DESKTOP = "desktop"
    COMMUNICATION = "communication"
    MEMORY = "memory"
    DEVOPS = "devops"
    RESEARCH = "research"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    """Schema for a single tool parameter."""

    name: str
    type: str  # "string" | "integer" | "boolean" | "array" | "object"
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None


@dataclass
class ToolMetadata:
    """Descriptive metadata for a tool."""

    name: str
    description: str
    category: ToolCategory = ToolCategory.CUSTOM
    parameters: list[ToolParameter] = field(default_factory=list)
    dangerous: bool = False  # requires user confirmation
    version: str = "1.0.0"

    def to_openai_schema(self) -> dict[str, Any]:
        """
        Convert to OpenAI function-calling schema.

        This allows the AI to understand and invoke this tool.
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop: dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


@dataclass
class ToolResult:
    """Standardised result from tool execution."""

    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {"success": self.success}
        if self.output is not None:
            d["output"] = self.output
        if self.error:
            d["error"] = self.error
        if self.metadata:
            d["metadata"] = self.metadata
        return d


class Tool(ABC):
    """
    Abstract base class for all Jarvis tools.

    Subclasses must implement ``execute()`` and provide ``metadata``.
    ``verify()`` is optional but recommended.
    """

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return the tool's metadata."""
        ...

    @abstractmethod
    async def execute(self, **params: Any) -> ToolResult:
        """Run the tool with the given parameters."""
        ...

    async def verify(self, result: ToolResult) -> bool:
        """
        Verify that the tool executed correctly.

        Default implementation checks ``result.success``.
        Override for domain-specific verification.
        """
        return result.success

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def is_dangerous(self) -> bool:
        return self.metadata.dangerous
