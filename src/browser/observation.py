"""Page observation utilities for context-limited observations."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.app.config import config
from src.browser.controller import BrowserController


@dataclass
class Observation:
    """Compact observation of current page state."""

    url: str
    title: str
    visible_text_summary: str
    screenshot_path: Optional[str]
    has_input_focused: bool
    scroll_position: dict
    timestamp: str

    def to_prompt_text(self) -> str:
        """Convert observation to text for LLM prompt."""
        parts = [
            f"URL: {self.url}",
            f"Title: {self.title}",
            f"Page summary: {self.visible_text_summary}",
        ]

        if self.screenshot_path:
            parts.append(f"Screenshot saved: {self.screenshot_path}")

        if self.has_input_focused:
            parts.append("Note: An input field is currently focused")

        parts.append(
            f"Scroll: {self.scroll_position.get('y', 0)}px from top, "
            f"page height: {self.scroll_position.get('height', 0)}px"
        )

        return "\n".join(parts)


class Observer:
    """Creates observations from browser state."""

    def __init__(self, browser: BrowserController, screenshots_dir: Path):
        self.browser = browser
        self.screenshots_dir = screenshots_dir
        self._screenshot_counter = 0

    async def observe(self, take_screenshot: bool = True) -> Observation:
        """
        Create a compact observation of the current page state.

        This is the main context-limiting mechanism - we don't dump
        the entire DOM, just a summary of visible content.
        """
        page = self.browser.page

        # Get basic info
        url = await self.browser.get_url()
        title = await self.browser.get_page_title()

        # Get visible text and summarize
        visible_text = await self.browser.get_visible_text(
            max_length=config.MAX_OBSERVATION_LENGTH
        )
        text_summary = self._create_summary(visible_text)

        # Check for focused input
        has_input_focused = await page.evaluate("""
            () => {
                const active = document.activeElement;
                return active && ['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName);
            }
        """)

        # Get scroll position
        scroll_position = await page.evaluate("""
            () => ({
                x: window.scrollX,
                y: window.scrollY,
                width: document.body.scrollWidth,
                height: document.body.scrollHeight,
                viewportHeight: window.innerHeight,
            })
        """)

        # Take screenshot if requested
        screenshot_path = None
        if take_screenshot:
            screenshot_path = await self._take_screenshot()

        return Observation(
            url=url,
            title=title,
            visible_text_summary=text_summary,
            screenshot_path=screenshot_path,
            has_input_focused=has_input_focused,
            scroll_position=scroll_position,
            timestamp=datetime.now().isoformat(),
        )

    async def _take_screenshot(self) -> str:
        """Take a screenshot and return the path."""
        self._screenshot_counter += 1
        filename = f"step_{self._screenshot_counter:04d}.png"
        path = self.screenshots_dir / filename
        await self.browser.take_screenshot(path)
        return str(path)

    def _create_summary(self, text: str, max_length: int = 500) -> str:
        """Create a brief summary of page text."""
        # Clean up and truncate
        text = " ".join(text.split())  # Normalize whitespace

        if len(text) <= max_length:
            return text

        # Try to end at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind(".")
        last_question = truncated.rfind("?")
        last_exclaim = truncated.rfind("!")

        best_end = max(last_period, last_question, last_exclaim)

        if best_end > max_length * 0.5:
            return truncated[: best_end + 1]

        return truncated + "..."
