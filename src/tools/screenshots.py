"""Screenshot tool."""

from pathlib import Path
from typing import Any

from src.browser.controller import BrowserController
from src.tools.registry import registry


def register_screenshot_tools(browser: BrowserController, screenshots_dir: Path) -> None:
    """Register screenshot tools."""

    _counter = {"value": 0}

    @registry.register(
        name="take_screenshot",
        description="Take a screenshot of the current page.",
        parameters={
            "full_page": {
                "type": "boolean",
                "description": "Whether to capture the full scrollable page (default: false)",
            },
        },
        required=[],
    )
    async def take_screenshot(full_page: bool = False) -> dict[str, Any]:
        _counter["value"] += 1
        filename = f"screenshot_{_counter['value']:04d}.png"
        path = screenshots_dir / filename

        await browser.take_screenshot(path, full_page=full_page)

        return {
            "path": str(path),
            "full_page": full_page,
        }
