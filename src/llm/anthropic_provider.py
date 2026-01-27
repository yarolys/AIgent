"""Anthropic Claude LLM provider."""

import json
from typing import Any

import anthropic

from src.app.config import config
from src.llm.base import LLMProvider, LLMResponse, ToolCall


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with tool calling support."""

    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.ANTHROPIC_MODEL

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LLMResponse:
        """Send chat request to Claude."""

        # Convert tools to Anthropic format
        anthropic_tools = self._convert_tools(tools)

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=anthropic_tools,
        )

        # Parse response
        content = None
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            stop_reason=response.stop_reason or "end_turn",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False,
    ) -> dict[str, Any]:
        """Format tool result for Anthropic conversation."""
        content = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result

        return {
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": content,
            "is_error": is_error,
        }

    def format_assistant_message(
        self,
        content: str | None,
        tool_calls: list[ToolCall],
    ) -> dict[str, Any]:
        """Format assistant message for Anthropic."""
        message_content: list[dict[str, Any]] = []

        if content:
            message_content.append({"type": "text", "text": content})

        for tc in tool_calls:
            message_content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.arguments,
            })

        return {"role": "assistant", "content": message_content}

    def format_tool_results_message(
        self,
        tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Format tool results for Anthropic - single user message with all results."""
        return [{"role": "user", "content": tool_results}]

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert tool definitions to Anthropic format."""
        anthropic_tools = []

        for tool in tools:
            anthropic_tools.append({
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"],
            })

        return anthropic_tools
