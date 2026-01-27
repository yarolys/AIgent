"""Browser action tools."""

from typing import Any

from src.browser.controller import BrowserController
from src.tools.registry import registry


def register_action_tools(browser: BrowserController) -> None:
    """Register all browser action tools."""

    @registry.register(
        name="navigate_to_url",
        description="Navigate the browser to a specific URL. Use this to go to websites.",
        parameters={
            "url": {
                "type": "string",
                "description": "The full URL to navigate to (must include http:// or https://)",
            },
        },
        required=["url"],
    )
    async def navigate_to_url(url: str) -> dict[str, Any]:
        await browser.navigate(url)
        return {"success": True, "url": await browser.get_url()}

    @registry.register(
        name="get_current_url",
        description="Get the current page URL.",
        parameters={},
        required=[],
    )
    async def get_current_url() -> dict[str, Any]:
        return {"url": await browser.get_url()}

    @registry.register(
        name="click",
        description=(
            "Click an element. You MUST provide the 'selector' from query_dom result. "
            "NEVER call this with an empty selector - always get selector from query_dom first."
        ),
        parameters={
            "selector": {
                "type": "string",
                "description": "The EXACT selector value from query_dom candidate (e.g., '[aria-label=\"Поиск\"]')",
            },
        },
        required=["selector"],
    )
    async def click(selector: str) -> dict[str, Any]:
        if not selector or not selector.strip():
            return {
                "success": False,
                "error": "Empty selector provided. You must first call query_dom() to find elements, then use the 'selector' value from the result.",
            }
        await browser.click(selector)
        return {"success": True, "clicked": selector}

    @registry.register(
        name="type_text",
        description=(
            "Type text into an input field. You MUST provide the 'selector' from query_dom result. "
            "NEVER call this with an empty selector. "
            "TIP: After typing in a search field, call press(keys='Enter') to submit."
        ),
        parameters={
            "selector": {
                "type": "string",
                "description": "The EXACT selector value from query_dom candidate (e.g., '[placeholder=\"Поиск\"]')",
            },
            "text": {
                "type": "string",
                "description": "Text to type into the element",
            },
            "clear": {
                "type": "boolean",
                "description": "Whether to clear existing text first (default: true)",
            },
        },
        required=["selector", "text"],
    )
    async def type_text(selector: str, text: str, clear: bool = True) -> dict[str, Any]:
        import os
        if os.environ.get("DEBUG_SELECTORS", "0") == "1":
            print(f"  [DEBUG] type_text called with selector={repr(selector)}")

        if not selector or not selector.strip():
            return {
                "success": False,
                "error": "Empty selector provided. You must first call query_dom() to find the input field, then use the 'selector' value from the result.",
            }
        await browser.type_text(selector, text, clear=clear)
        return {
            "success": True,
            "typed": text[:50] + "..." if len(text) > 50 else text,
            "hint": "If this is a search field, call press(keys='Enter') to submit",
        }

    @registry.register(
        name="press",
        description="Press keyboard keys. Examples: Enter, Escape, Tab, ArrowDown.",
        parameters={
            "keys": {
                "type": "string",
                "description": "Key or key combination to press",
            },
        },
        required=["keys"],
    )
    async def press(keys: str) -> dict[str, Any]:
        await browser.press_key(keys)
        return {"success": True, "pressed": keys}

    @registry.register(
        name="scroll",
        description="Scroll the page. Positive values scroll down, negative scroll up.",
        parameters={
            "amount": {
                "type": "integer",
                "description": "Pixels to scroll (positive=down, negative=up).",
            },
        },
        required=["amount"],
    )
    async def scroll(amount: int) -> dict[str, Any]:
        await browser.scroll(amount)
        direction = "down" if amount > 0 else "up"
        return {"success": True, "scrolled": f"{abs(amount)}px {direction}"}

    @registry.register(
        name="wait",
        description="Wait for a specified number of seconds. Use when page needs time to load.",
        parameters={
            "seconds": {
                "type": "number",
                "description": "Seconds to wait (max 10)",
            },
        },
        required=["seconds"],
    )
    async def wait(seconds: float) -> dict[str, Any]:
        import asyncio
        seconds = min(seconds, 10.0)  # Cap at 10 seconds
        await asyncio.sleep(seconds)
        return {"success": True, "waited": f"{seconds}s"}

    @registry.register(
        name="hover",
        description="Hover over an element. Use the 'selector' from query_dom result.",
        parameters={
            "selector": {
                "type": "string",
                "description": "The EXACT selector value from query_dom candidate",
            },
        },
        required=["selector"],
    )
    async def hover(selector: str) -> dict[str, Any]:
        if not selector or not selector.strip():
            return {
                "success": False,
                "error": "Empty selector provided. First call query_dom() to find the element.",
            }
        await browser.hover(selector)
        return {"success": True, "hovered": selector}

    @registry.register(
        name="back",
        description="Navigate back to the previous page in browser history.",
        parameters={},
        required=[],
    )
    async def back() -> dict[str, Any]:
        await browser.go_back()
        return {"success": True, "url": await browser.get_url()}

    @registry.register(
        name="close_popups",
        description="Try to close any visible popups, modals, or cookie banners.",
        parameters={},
        required=[],
    )
    async def close_popups() -> dict[str, Any]:
        closed = await browser.close_popups()
        return {"success": True, "closed_something": closed}
