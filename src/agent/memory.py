"""Memory management for agent context."""

from dataclasses import dataclass, field
from typing import Any

from src.app.config import config
from src.utils.text import compress_history


@dataclass
class Step:
    """A single step in agent history."""

    step_number: int
    action: str
    tool_name: str
    tool_args: dict[str, Any]
    result_summary: str
    success: bool
    observation_summary: str = ""


@dataclass
class AgentMemory:
    """Manages agent memory with context compression."""

    task: str
    steps: list[Step] = field(default_factory=list)
    state_summary: str = ""
    total_tokens_used: int = 0

    def add_step(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        result_summary: str,
        success: bool,
        observation_summary: str = "",
    ) -> None:
        """Add a new step to history."""
        step = Step(
            step_number=len(self.steps) + 1,
            action=f"{tool_name}({self._format_args(tool_args)})",
            tool_name=tool_name,
            tool_args=tool_args,
            result_summary=result_summary,
            success=success,
            observation_summary=observation_summary,
        )
        self.steps.append(step)

        # Update state summary
        self._update_state_summary()

    def get_history_summary(self) -> str:
        """Get compressed history for prompt."""
        if not self.steps:
            return "No previous actions."

        # Convert steps to dict format for compression
        step_dicts = [
            {
                "action": s.action,
                "result_summary": s.result_summary,
                "success": s.success,
            }
            for s in self.steps
        ]

        return compress_history(step_dicts, max_steps=config.MAX_HISTORY_STEPS)

    def get_recent_failures(self, n: int = 3) -> list[Step]:
        """Get recent failed steps for error recovery."""
        failures = [s for s in self.steps if not s.success]
        return failures[-n:]

    def get_last_step(self) -> Step | None:
        """Get the most recent step."""
        return self.steps[-1] if self.steps else None

    def update_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """Track token usage."""
        self.total_tokens_used += input_tokens + output_tokens

    def _update_state_summary(self) -> None:
        """Update the state summary based on recent actions."""
        if not self.steps:
            self.state_summary = "Just started."
            return

        last_step = self.steps[-1]

        # Track important state changes
        summaries = []

        # Count actions by type
        action_counts: dict[str, int] = {}
        for step in self.steps:
            action_counts[step.tool_name] = action_counts.get(step.tool_name, 0) + 1

        # Success rate
        success_count = sum(1 for s in self.steps if s.success)
        total = len(self.steps)

        summaries.append(f"Steps: {total} ({success_count} successful)")

        # Last action
        summaries.append(f"Last: {last_step.action} -> {last_step.result_summary}")

        # Recent observation
        if last_step.observation_summary:
            summaries.append(f"Current page: {last_step.observation_summary[:100]}")

        self.state_summary = " | ".join(summaries)

    def _format_args(self, args: dict[str, Any], max_len: int = 50) -> str:
        """Format arguments compactly."""
        parts = []
        for k, v in args.items():
            v_str = str(v)
            if len(v_str) > 30:
                v_str = v_str[:27] + "..."
            parts.append(f"{k}={v_str}")

        result = ", ".join(parts)
        if len(result) > max_len:
            result = result[: max_len - 3] + "..."
        return result

    def to_messages(self) -> list[dict[str, Any]]:
        """Convert memory to message format for LLM."""
        # This is handled by the orchestrator which maintains
        # the full conversation. Memory just tracks our state.
        return []
