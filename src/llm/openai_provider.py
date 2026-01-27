"""OpenAI LLM provider."""

import json
from typing import Any

import openai

from src.app.config import config
from src.llm.base import LLMProvider, LLMResponse, ToolCall


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider with tool calling support."""

    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LLMResponse:
        """Send chat request to OpenAI."""

        # Prepend system message
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        # Convert tools to OpenAI format
        openai_tools = self._convert_tools(tools)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            tools=openai_tools if openai_tools else None,
            max_tokens=4096,
        )

        choice = response.choices[0]
        message = choice.message

        # Parse tool calls
        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    arguments = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=arguments,
                    )
                )

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "stop",
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
        is_error: bool = False,
    ) -> dict[str, Any]:
        """Format tool result for OpenAI conversation."""
        content = json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result

        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }

    def format_assistant_message(
        self,
        content: str | None,
        tool_calls: list[ToolCall],
    ) -> dict[str, Any]:
        """Format assistant message for OpenAI."""
        message: dict[str, Any] = {"role": "assistant"}

        if content:
            message["content"] = content

        if tool_calls:
            message["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in tool_calls
            ]

        return message

    def format_tool_results_message(
        self,
        tool_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Format tool results for OpenAI - each result is a separate message."""
        # OpenAI expects each tool result as a separate message
        return tool_results

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert tool definitions to OpenAI format."""
        openai_tools = []

        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            })

        return openai_tools
