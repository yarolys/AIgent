"""Tool registry for LLM tool calling."""

from typing import Any, Callable, TypedDict


class ToolParameter(TypedDict, total=False):
    """Tool parameter definition."""

    type: str
    description: str
    enum: list[str]
    default: Any


class ToolDefinition(TypedDict):
    """Tool definition for LLM."""

    name: str
    description: str
    parameters: dict[str, Any]


class ToolRegistry:
    """Registry of tools available to the agent."""

    def __init__(self):
        self._tools: dict[str, Callable[..., Any]] = {}
        self._definitions: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, ToolParameter],
        required: list[str] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a tool."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[name] = func
            self._definitions[name] = {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required or [],
                },
            }
            return func

        return decorator

    def get_tool(self, name: str) -> Callable[..., Any] | None:
        """Get a tool function by name."""
        return self._tools.get(name)

    def get_all_definitions(self) -> list[ToolDefinition]:
        """Get all tool definitions for LLM."""
        return list(self._definitions.values())

    def get_definition(self, name: str) -> ToolDefinition | None:
        """Get a specific tool definition."""
        return self._definitions.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())


# Global registry instance
registry = ToolRegistry()
