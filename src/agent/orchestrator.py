"""Main agent orchestrator with plan/act/observe loop."""

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.agent.errors import ErrorContext, ErrorHandler, RecoveryStrategy
from src.agent.memory import AgentMemory
from src.agent.policies import security_policy
from src.agent.prompts import SYSTEM_PROMPT, create_task_prompt
from src.agent.subagents.dom_analyst import DOMAnalyst
from src.app.config import config
from src.app.logging import RunLogger, get_user_confirmation
from src.browser.controller import BrowserController
from src.browser.observation import Observer
from src.llm.base import LLMProvider, LLMResponse
from src.tools.registry import registry


class AgentStatus(Enum):
    """Agent execution status."""

    RUNNING = "running"
    DONE = "done"
    NEED_USER_INPUT = "need_user_input"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of agent execution."""

    status: AgentStatus
    summary: str
    steps_taken: int
    final_url: str


class Orchestrator:
    """
    Main agent orchestrator implementing the plan/act/observe loop.

    The orchestrator:
    1. Receives a task from the user
    2. Observes the current page state
    3. Asks the LLM for the next action
    4. Executes the action (with security checks)
    5. Observes the result
    6. Repeats until done/failed/needs input
    """

    def __init__(
        self,
        browser: BrowserController,
        llm: LLMProvider,
        logger: RunLogger,
    ):
        self.browser = browser
        self.llm = llm
        self.logger = logger
        self.observer = Observer(browser, logger.screenshots_dir)
        self.dom_analyst = DOMAnalyst(llm, logger)
        self.error_handler = ErrorHandler()
        self.security = security_policy

        self.memory: AgentMemory | None = None
        self.messages: list[dict[str, Any]] = []
        self._should_stop = False

    async def execute_task(self, task: str) -> ExecutionResult:
        """
        Execute a task autonomously.

        Args:
            task: Natural language task description

        Returns:
            ExecutionResult with status and summary
        """
        self.memory = AgentMemory(task=task)
        self.messages = []
        self._should_stop = False
        self.error_handler.reset()

        self.logger.log_agent_thought(f"Starting task: {task}")

        step_count = 0

        while step_count < config.MAX_STEPS and not self._should_stop:
            step_count += 1

            try:
                # 1. Observe current state
                observation = await self.observer.observe()
                observation_text = observation.to_prompt_text()

                # 2. Get history summary (context compression)
                history_summary = self.memory.get_history_summary()

                # 3. Create prompt and get LLM response
                user_prompt = create_task_prompt(task, observation_text, history_summary)

                if not self.messages:
                    # First message
                    self.messages.append({"role": "user", "content": user_prompt})
                else:
                    # Continue conversation - add observation update
                    self.messages.append({
                        "role": "user",
                        "content": f"Current state:\n{observation_text}\n\nContinue with the task.",
                    })

                # 4. Get LLM decision
                response = await self._get_llm_response()

                if not response:
                    return ExecutionResult(
                        status=AgentStatus.FAILED,
                        summary="LLM did not respond",
                        steps_taken=step_count,
                        final_url=await self.browser.get_url(),
                    )

                # 5. Process response
                result = await self._process_response(response, observation.url)

                if result:
                    return result

                # Track token usage
                self.memory.update_tokens(
                    response.usage.get("input_tokens", 0),
                    response.usage.get("output_tokens", 0),
                )

            except Exception as e:
                self.logger.log_error(f"Step {step_count} error: {e}")

                # Try to recover
                if step_count < config.MAX_STEPS - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    return ExecutionResult(
                        status=AgentStatus.FAILED,
                        summary=f"Error: {e}",
                        steps_taken=step_count,
                        final_url=await self.browser.get_url(),
                    )

        # Max steps reached
        return ExecutionResult(
            status=AgentStatus.FAILED,
            summary=f"Max steps ({config.MAX_STEPS}) reached without completion",
            steps_taken=step_count,
            final_url=await self.browser.get_url(),
        )

    async def _get_llm_response(self) -> LLMResponse | None:
        """Get response from LLM."""
        tools = registry.get_all_definitions()

        response = await self.llm.chat(
            messages=self.messages,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )

        # Add assistant response to messages using provider-specific format
        if response.content or response.tool_calls:
            assistant_msg = self.llm.format_assistant_message(
                response.content,
                response.tool_calls,
            )
            self.messages.append(assistant_msg)

        return response

    async def _process_response(
        self,
        response: LLMResponse,
        current_url: str,
    ) -> ExecutionResult | None:
        """
        Process LLM response, execute tools, check for completion.

        Returns ExecutionResult if done, None to continue.
        """
        # Check for completion signals in text
        if response.content:
            content_upper = response.content.upper()

            if "DONE:" in content_upper:
                summary = response.content.split("DONE:", 1)[-1].strip()
                self.logger.log_agent_thought(f"Task complete: {summary}")
                return ExecutionResult(
                    status=AgentStatus.DONE,
                    summary=summary,
                    steps_taken=len(self.memory.steps) if self.memory else 0,
                    final_url=await self.browser.get_url(),
                )

            if "NEED_USER_INPUT:" in content_upper:
                reason = response.content.split("NEED_USER_INPUT:", 1)[-1].strip()
                self.logger.log_agent_thought(f"Needs user input: {reason}")
                return ExecutionResult(
                    status=AgentStatus.NEED_USER_INPUT,
                    summary=reason,
                    steps_taken=len(self.memory.steps) if self.memory else 0,
                    final_url=await self.browser.get_url(),
                )

            if "FAILED:" in content_upper:
                reason = response.content.split("FAILED:", 1)[-1].strip()
                self.logger.log_agent_thought(f"Task failed: {reason}")
                return ExecutionResult(
                    status=AgentStatus.FAILED,
                    summary=reason,
                    steps_taken=len(self.memory.steps) if self.memory else 0,
                    final_url=await self.browser.get_url(),
                )

            # Log thought if present
            if response.content and not response.tool_calls:
                self.logger.log_agent_thought(response.content[:200])

        # Execute tool calls
        if response.tool_calls:
            tool_results = []

            for tc in response.tool_calls:
                result = await self._execute_tool(
                    tc.id,
                    tc.name,
                    tc.arguments,
                    current_url,
                )
                tool_results.append(result)

                # Check if security blocked
                if result.get("blocked"):
                    return ExecutionResult(
                        status=AgentStatus.CANCELLED,
                        summary="User cancelled action",
                        steps_taken=len(self.memory.steps) if self.memory else 0,
                        final_url=await self.browser.get_url(),
                    )

            # Add tool results to messages using provider-specific format
            result_messages = self.llm.format_tool_results_message(tool_results)
            self.messages.extend(result_messages)

        return None  # Continue execution

    async def _execute_tool(
        self,
        tool_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        current_url: str,
    ) -> dict[str, Any]:
        """Execute a single tool with security checks and error handling."""
        # Security check
        page_text = await self.browser.get_visible_text(max_length=500)
        classification = self.security.classify_action(
            tool_name,
            tool_args,
            current_url,
            page_text,
        )

        if classification.requires_confirmation:
            self.logger.log_security_check(
                self.security.format_confirmation_request(tool_name, tool_args, classification),
                classification.reason,
            )

            if not get_user_confirmation("Proceed with this action?"):
                self.logger.log_agent_thought("Action cancelled by user")
                return self.llm.format_tool_result(
                    tool_id,
                    {"error": "Action cancelled by user", "blocked": True},
                    is_error=True,
                )

        # Get tool function
        tool_func = registry.get_tool(tool_name)
        if not tool_func:
            error_result = {"error": f"Unknown tool: {tool_name}"}
            self.logger.log_tool_call(tool_name, tool_args, error_result, success=False)
            return self.llm.format_tool_result(tool_id, error_result, is_error=True)

        # Execute with error handling
        action_key = self.error_handler.get_action_key(tool_name, tool_args)

        try:
            result = await tool_func(**tool_args)

            # Log success
            self.logger.log_tool_call(tool_name, tool_args, result, success=True)

            # Update memory
            if self.memory:
                observation = await self.observer.observe(take_screenshot=False)
                self.memory.add_step(
                    tool_name,
                    tool_args,
                    str(result)[:100],
                    success=True,
                    observation_summary=observation.url,
                )

            self.error_handler.track_action(action_key, success=True)
            return self.llm.format_tool_result(tool_id, result)

        except Exception as e:
            error_msg = str(e)
            retry_count = self.error_handler.track_action(action_key, success=False)

            self.logger.log_tool_call(
                tool_name,
                tool_args,
                {"error": error_msg},
                success=False,
            )

            # Get recovery strategy
            context = ErrorContext(
                error_type=type(e).__name__,
                error_message=error_msg,
                tool_name=tool_name,
                tool_args=tool_args,
                retry_count=retry_count,
                recent_failures=[],
            )

            recovery = self.error_handler.get_recovery_strategy(context)

            if recovery.strategy != RecoveryStrategy.GIVE_UP and recovery.tool_name:
                # Execute recovery action
                self.logger.log_agent_thought(f"Recovery: {recovery.description}")
                try:
                    recovery_tool = registry.get_tool(recovery.tool_name)
                    if recovery_tool and recovery.tool_args:
                        await recovery_tool(**recovery.tool_args)
                except Exception:
                    pass  # Recovery failed, continue with error

            # Update memory
            if self.memory:
                self.memory.add_step(
                    tool_name,
                    tool_args,
                    f"Error: {error_msg[:50]}",
                    success=False,
                )

            return self.llm.format_tool_result(
                tool_id,
                {"error": error_msg, "recovery_attempted": recovery.description},
                is_error=True,
            )

    def stop(self) -> None:
        """Signal the agent to stop."""
        self._should_stop = True
