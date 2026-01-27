"""Security policies for action classification and confirmation."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionRisk(Enum):
    """Risk level of an action."""

    SAFE = "safe"
    MODERATE = "moderate"
    DESTRUCTIVE = "destructive"


@dataclass
class ActionClassification:
    """Classification result for an action."""

    risk: ActionRisk
    reason: str
    requires_confirmation: bool


# Keywords indicating destructive actions (case-insensitive)
DESTRUCTIVE_KEYWORDS = {
    # Payment/Purchase
    "pay", "payment", "оплат", "купить", "buy", "purchase", "checkout",
    "order", "заказ", "подтвердить заказ", "confirm order", "place order",
    "оформить", "proceed to payment",

    # Delete/Remove
    "delete", "удалить", "remove", "убрать", "clear", "очистить",
    "trash", "корзина", "spam", "спам",

    # Send/Submit
    "send", "отправить", "submit", "опубликовать", "publish", "post",

    # Account actions
    "unsubscribe", "отписаться", "cancel subscription", "отменить подписку",
    "logout", "выйти", "sign out",
}

# Keywords indicating input fields that need care
SENSITIVE_INPUT_KEYWORDS = {
    "card", "карт", "cvv", "cvc", "credit", "debit",
    "password", "пароль", "pin", "пин",
    "ssn", "social security",
}

# URL patterns for payment pages
PAYMENT_URL_PATTERNS = [
    "checkout", "payment", "pay", "order",
    "cart", "basket", "корзина",
]


class SecurityPolicy:
    """Evaluates actions for security risks."""

    def classify_action(
        self,
        tool_name: str,
        args: dict[str, Any],
        page_url: str = "",
        page_text: str = "",
    ) -> ActionClassification:
        """
        Classify an action's risk level.

        Returns ActionClassification with risk level and whether
        user confirmation is required.
        """
        # Navigation is generally safe
        if tool_name in ["navigate_to_url", "get_current_url", "take_screenshot", "wait", "scroll"]:
            return ActionClassification(
                risk=ActionRisk.SAFE,
                reason="Read-only or navigation action",
                requires_confirmation=False,
            )

        # query_dom and close_popups are safe
        if tool_name in ["query_dom", "close_popups", "hover", "back"]:
            return ActionClassification(
                risk=ActionRisk.SAFE,
                reason="Non-modifying action",
                requires_confirmation=False,
            )

        # For click actions, analyze what's being clicked
        if tool_name == "click":
            return self._classify_click(args, page_url, page_text)

        # For type actions, check if it's sensitive data
        if tool_name == "type_text":
            return self._classify_type(args, page_url)

        # For press actions, check for Enter on forms
        if tool_name == "press":
            return self._classify_press(args, page_url, page_text)

        # Default to moderate for unknown tools
        return ActionClassification(
            risk=ActionRisk.MODERATE,
            reason="Unknown action type",
            requires_confirmation=False,
        )

    def _classify_click(
        self,
        args: dict[str, Any],
        page_url: str,
        page_text: str,
    ) -> ActionClassification:
        """Classify a click action."""
        selector = str(args.get("selector", "")).lower()

        # Check if clicking something that sounds destructive
        for keyword in DESTRUCTIVE_KEYWORDS:
            if keyword in selector:
                return ActionClassification(
                    risk=ActionRisk.DESTRUCTIVE,
                    reason=f"Click on element containing '{keyword}'",
                    requires_confirmation=True,
                )

        # Check if on a payment page
        url_lower = page_url.lower()
        for pattern in PAYMENT_URL_PATTERNS:
            if pattern in url_lower:
                # On payment page, be more careful
                risky_keywords = ["submit", "confirm", "оформить", "заказ", "order"]
                if any(kw in selector for kw in risky_keywords):
                    return ActionClassification(
                        risk=ActionRisk.DESTRUCTIVE,
                        reason="Submit/confirm action on payment-related page",
                        requires_confirmation=True,
                    )

        return ActionClassification(
            risk=ActionRisk.SAFE,
            reason="Regular click action",
            requires_confirmation=False,
        )

    def _classify_type(
        self,
        args: dict[str, Any],
        page_url: str,
    ) -> ActionClassification:
        """Classify a type action."""
        selector = str(args.get("selector", "")).lower()
        text = str(args.get("text", ""))

        # Check if typing into sensitive field
        for keyword in SENSITIVE_INPUT_KEYWORDS:
            if keyword in selector:
                return ActionClassification(
                    risk=ActionRisk.DESTRUCTIVE,
                    reason=f"Typing into sensitive field containing '{keyword}'",
                    requires_confirmation=True,
                )

        # Text that looks like payment info
        if any(c.isdigit() for c in text):
            # Check for card number patterns (16 digits with optional spaces/dashes)
            digits_only = "".join(c for c in text if c.isdigit())
            if len(digits_only) >= 13:
                return ActionClassification(
                    risk=ActionRisk.DESTRUCTIVE,
                    reason="Text appears to be payment card number",
                    requires_confirmation=True,
                )

        return ActionClassification(
            risk=ActionRisk.SAFE,
            reason="Regular text input",
            requires_confirmation=False,
        )

    def _classify_press(
        self,
        args: dict[str, Any],
        page_url: str,
        page_text: str,
    ) -> ActionClassification:
        """Classify a key press action."""
        keys = str(args.get("keys", "")).lower()

        # Enter key might submit forms
        if "enter" in keys:
            url_lower = page_url.lower()
            # On payment/order pages, Enter is risky
            for pattern in PAYMENT_URL_PATTERNS:
                if pattern in url_lower:
                    return ActionClassification(
                        risk=ActionRisk.MODERATE,
                        reason="Enter key on payment-related page",
                        requires_confirmation=True,
                    )

        return ActionClassification(
            risk=ActionRisk.SAFE,
            reason="Regular key press",
            requires_confirmation=False,
        )

    def format_confirmation_request(
        self,
        tool_name: str,
        args: dict[str, Any],
        classification: ActionClassification,
    ) -> str:
        """Format a user-friendly confirmation request."""
        action_desc = self._describe_action(tool_name, args)

        return (
            f"Action: {action_desc}\n"
            f"Risk: {classification.risk.value}\n"
            f"Reason: {classification.reason}\n\n"
            f"Do you want to proceed with this action?"
        )

    def _describe_action(self, tool_name: str, args: dict[str, Any]) -> str:
        """Create human-readable action description."""
        if tool_name == "click":
            return f"Click on element: {args.get('selector', 'unknown')}"
        if tool_name == "type_text":
            text = args.get("text", "")
            if len(text) > 30:
                text = text[:27] + "..."
            return f"Type '{text}' into {args.get('selector', 'unknown')}"
        if tool_name == "press":
            return f"Press key: {args.get('keys', 'unknown')}"
        return f"{tool_name}({args})"


# Global policy instance
security_policy = SecurityPolicy()
