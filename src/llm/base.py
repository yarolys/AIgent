"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str | None  # Text response
    tool_calls: list[ToolCall]  # Tool calls to execute
    stop_reason: str  # 'end_turn', 'tool_use', 'max_tokens'
    usage: dict[str, int]  # Token usage


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LLMResponse:
        """
        Send a chat completion request.

        Args:
            messages: Conversation history
            tools: Tool definitions
            system_prompt: System prompt

        Returns:
            LLMResponse with content and/or tool calls
        """
        pass

    @abstractmethod
    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False,
    ) -> dict[str, Any]:
        """Format a tool result for the conversation."""
        pass

    @abstractmethod
    def format_assistant_message(
        self,
        content: str | None,
        tool_calls: list["ToolCall"],
    ) -> dict[str, Any]:
        """Format an assistant message with optional tool calls."""
        pass

    @abstractmethod
    def format_tool_results_message(
        self,
        tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Format tool results as message(s). Returns list of messages to add."""
        pass
