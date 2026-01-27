"""Error handling and recovery strategies."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.app.config import config


class RecoveryStrategy(Enum):
    """Available recovery strategies."""

    RETRY = "retry"  # Retry the same action
    ALTERNATIVE = "alternative"  # Try alternative element
    SCROLL = "scroll"  # Scroll and retry
    WAIT = "wait"  # Wait and retry
    CLOSE_POPUP = "close_popup"  # Close popups and retry
    GO_BACK = "go_back"  # Navigate back
    GIVE_UP = "give_up"  # Stop trying


@dataclass
class ErrorContext:
    """Context for error recovery decisions."""

    error_type: str
    error_message: str
    tool_name: str
    tool_args: dict[str, Any]
    retry_count: int
    recent_failures: list[dict[str, Any]]


@dataclass
class RecoveryAction:
    """A recovery action to attempt."""

    strategy: RecoveryStrategy
    description: str
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None


class ErrorHandler:
    """Handles errors and determines recovery strategies."""

    def __init__(self):
        self._retry_counts: dict[str, int] = {}

    def get_recovery_strategy(self, context: ErrorContext) -> RecoveryAction:
        """Determine the best recovery strategy for an error."""
        error_lower = context.error_message.lower()

        # Element not found errors
        not_found_keywords = ["not found", "no element", "timeout", "waiting for selector"]
        if any(kw in error_lower for kw in not_found_keywords):
            return self._handle_element_not_found(context)

        # Element not visible/clickable
        if any(kw in error_lower for kw in ["not visible", "intercepted", "obscured", "covered"]):
            return self._handle_element_obscured(context)

        # Navigation errors
        if any(kw in error_lower for kw in ["navigation", "net::", "err_"]):
            return self._handle_navigation_error(context)

        # Default: retry with wait
        if context.retry_count < config.MAX_RETRIES:
            return RecoveryAction(
                strategy=RecoveryStrategy.WAIT,
                description="Wait and retry",
                tool_name="wait",
                tool_args={"seconds": 2.0},
            )

        return RecoveryAction(
            strategy=RecoveryStrategy.GIVE_UP,
            description=f"Failed after {context.retry_count} attempts: {context.error_message}",
        )

    def _handle_element_not_found(self, context: ErrorContext) -> RecoveryAction:
        """Handle element not found errors."""
        if context.retry_count == 0:
            # First try: wait for dynamic content
            return RecoveryAction(
                strategy=RecoveryStrategy.WAIT,
                description="Wait for element to appear",
                tool_name="wait",
                tool_args={"seconds": 2.0},
            )

        if context.retry_count == 1:
            # Second try: scroll to find element
            return RecoveryAction(
                strategy=RecoveryStrategy.SCROLL,
                description="Scroll down to find element",
                tool_name="scroll",
                tool_args={"amount": 500},
            )

        if context.retry_count == 2:
            # Third try: scroll up
            return RecoveryAction(
                strategy=RecoveryStrategy.SCROLL,
                description="Scroll up to find element",
                tool_name="scroll",
                tool_args={"amount": -500},
            )

        # Give up and suggest alternative
        return RecoveryAction(
            strategy=RecoveryStrategy.ALTERNATIVE,
            description="Element not found - try query_dom with different query",
        )

    def _handle_element_obscured(self, context: ErrorContext) -> RecoveryAction:
        """Handle element obscured/intercepted errors."""
        if context.retry_count == 0:
            # First: try closing popups
            return RecoveryAction(
                strategy=RecoveryStrategy.CLOSE_POPUP,
                description="Close popups that may be blocking",
                tool_name="close_popups",
                tool_args={},
            )

        if context.retry_count == 1:
            # Scroll element into better view
            return RecoveryAction(
                strategy=RecoveryStrategy.SCROLL,
                description="Scroll to better position element",
                tool_name="scroll",
                tool_args={"amount": -200},
            )

        if context.retry_count == 2:
            # Wait for animations
            return RecoveryAction(
                strategy=RecoveryStrategy.WAIT,
                description="Wait for animations/overlays",
                tool_name="wait",
                tool_args={"seconds": 1.5},
            )

        return RecoveryAction(
            strategy=RecoveryStrategy.ALTERNATIVE,
            description="Element obscured - try alternative selector",
        )

    def _handle_navigation_error(self, context: ErrorContext) -> RecoveryAction:
        """Handle navigation/network errors."""
        if context.retry_count < 2:
            return RecoveryAction(
                strategy=RecoveryStrategy.WAIT,
                description="Wait and retry navigation",
                tool_name="wait",
                tool_args={"seconds": 3.0},
            )

        return RecoveryAction(
            strategy=RecoveryStrategy.GIVE_UP,
            description="Navigation failed - network issue",
        )

    def track_action(self, action_key: str, success: bool) -> int:
        """Track action attempts and return retry count."""
        if success:
            self._retry_counts.pop(action_key, None)
            return 0

        self._retry_counts[action_key] = self._retry_counts.get(action_key, 0) + 1
        return self._retry_counts[action_key]

    def reset(self) -> None:
        """Reset all retry counters."""
        self._retry_counts.clear()

    def get_action_key(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """Generate a unique key for an action."""
        # Use tool name + main argument
        if tool_name == "click":
            return f"click:{tool_args.get('selector', '')}"
        if tool_name == "type_text":
            return f"type:{tool_args.get('selector', '')}"
        if tool_name == "navigate_to_url":
            return f"nav:{tool_args.get('url', '')}"
        return f"{tool_name}:{hash(str(tool_args))}"


# Global error handler instance
error_handler = ErrorHandler()
