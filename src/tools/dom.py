"""DOM query tool for finding interactive elements."""

import os
from typing import Any

from src.app.config import config
from src.browser.controller import BrowserController
from src.tools.registry import registry

# Debug mode - set DEBUG_SELECTORS=1 in environment to see raw element data
DEBUG_SELECTORS = os.environ.get("DEBUG_SELECTORS", "0") == "1"


def register_dom_tools(browser: BrowserController) -> None:
    """Register DOM query tools."""

    @registry.register(
        name="query_dom",
        description=(
            "Search for interactive elements on the page. Returns candidates with 'selector' field. "
            "IMPORTANT: You MUST use query_dom FIRST, then copy the EXACT 'selector' value from "
            "the result and use it in click() or type_text(). "
            "Example workflow: "
            "1. query_dom('search') -> returns candidates with selectors "
            "2. Pick the best candidate "
            "3. Use its 'selector' value in type_text(selector=..., text=...)"
        ),
        parameters={
            "query": {
                "type": "string",
                "description": (
                    "Search query to match elements. Examples: 'search', 'login', 'submit', "
                    "'email input', 'add to cart', 'В корзину'. Leave empty to get all interactive elements."
                ),
            },
            "limit": {
                "type": "integer",
                "description": f"Maximum number of results (default: {config.QUERY_DOM_LIMIT})",
            },
        },
        required=["query"],
    )
    async def query_dom(query: str, limit: int | None = None) -> dict[str, Any]:
        if limit is None:
            limit = config.QUERY_DOM_LIMIT

        elements = await browser.query_interactive_elements(query, limit=limit)

        # Format for LLM consumption
        candidates = []
        for i, elem in enumerate(elements):
            # Ensure we have a valid selector
            selector = elem.get("selector", "")

            # Multiple fallback attempts if selector is invalid
            if not selector or selector == "body" or selector.startswith("POSITION_FALLBACK"):
                # Generate fallback selector from available info
                if elem.get("ariaLabel"):
                    selector = f'[aria-label="{elem["ariaLabel"][:50]}"]'
                elif elem.get("placeholder"):
                    selector = f'[placeholder="{elem["placeholder"][:50]}"]'
                elif elem.get("name"):
                    selector = f'[name="{elem["name"][:50]}"]'
                elif elem.get("text"):
                    tag = elem.get("tag", "").lower() or "*"
                    text = elem["text"][:30].replace('"', '\\"')
                    selector = f'{tag}:has-text("{text}")'
                elif elem.get("cssPath"):
                    selector = elem.get("cssPath", "")
                elif elem.get("tag"):
                    tag = elem.get("tag", "").lower()
                    if tag == "input":
                        input_type = elem.get("attributes", {}).get("type", "text")
                        selector = f'input[type="{input_type}"]'
                    else:
                        selector = tag

            # Skip candidates without valid selector
            if not selector or selector == "body":
                continue

            candidate = {
                "id": i,
                "role": elem.get("role", "unknown"),
                "text": elem.get("text", "")[:100],
                "selector": selector,
            }

            # Add useful identifying info
            if elem.get("ariaLabel"):
                candidate["aria_label"] = elem["ariaLabel"][:50]
            if elem.get("placeholder"):
                candidate["placeholder"] = elem["placeholder"][:50]
            if elem.get("name"):
                candidate["name"] = elem["name"][:50]

            # Add position info
            bbox = elem.get("bbox", {})
            if bbox:
                candidate["position"] = f"({bbox.get('x', 0)}, {bbox.get('y', 0)})"
                candidate["in_viewport"] = elem.get("inViewport", False)

            candidates.append(candidate)

        # Provide usage hint if candidates found
        usage_hint = ""
        if candidates:
            usage_hint = f"Use click(selector=\"{candidates[0]['selector']}\") or type_text(selector=\"{candidates[0]['selector']}\", text=\"...\")"

        return {
            "candidates": candidates,
            "total_found": len(candidates),
            "query": query,
            "usage_hint": usage_hint,
        }

    @registry.register(
        name="get_all_elements",
        description=(
            "Get ALL visible interactive elements on the page without text filtering. "
            "Use this when query_dom returns no results to see what elements exist. "
            "Returns up to 30 elements with their text and selectors."
        ),
        parameters={
            "limit": {
                "type": "integer",
                "description": "Maximum number of elements to return (default: 30)",
            },
        },
        required=[],
    )
    async def get_all_elements(limit: int = 30) -> dict[str, Any]:
        """Get all interactive elements without text filtering."""
        elements = await browser.query_interactive_elements("", limit=limit)

        # Format for display
        items = []
        for i, elem in enumerate(elements):
            text = elem.get("text", "")[:60]
            tag = elem.get("tag", "?")
            selector = elem.get("selector", "")

            # Get best identifier
            identifier = (
                elem.get("ariaLabel") or
                elem.get("placeholder") or
                elem.get("name") or
                text[:30] or
                selector[:50]
            )

            items.append({
                "index": i,
                "tag": tag,
                "text": text,
                "identifier": identifier[:50] if identifier else "N/A",
                "selector": selector,
            })

        return {
            "elements": items,
            "total": len(items),
            "hint": "Use the 'selector' value with click() or type_text()",
        }
