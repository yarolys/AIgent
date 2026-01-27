"""Browser controller using Playwright with persistent context."""

import asyncio
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from src.app.config import config


class BrowserController:
    """Controls browser instance with persistent session support."""

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def page(self) -> Page:
        """Get the current page, raising if not initialized."""
        if self._page is None:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page

    async def start(self) -> None:
        """Start browser with persistent context."""
        config.ensure_dirs()

        self._playwright = await async_playwright().start()

        # Use persistent context for session persistence
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(config.USER_DATA_DIR),
            headless=config.HEADLESS,
            viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
            locale="ru-RU",  # Can be configured
            timezone_id="Europe/Moscow",  # Can be configured
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )

        # Get or create a page
        pages = self._context.pages
        if pages:
            self._page = pages[0]
        else:
            self._page = await self._context.new_page()

        # Set default timeout
        self._page.set_default_timeout(config.BROWSER_TIMEOUT)

    async def stop(self) -> None:
        """Stop the browser."""
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

        self._page = None
        self._context = None
        self._playwright = None

    async def navigate(self, url: str) -> None:
        """Navigate to a URL."""
        await self.page.goto(url, wait_until="domcontentloaded")
        await self._wait_for_stability()

    async def get_url(self) -> str:
        """Get current URL."""
        return self.page.url

    async def click(self, selector: str) -> None:
        """Click an element."""
        await self.page.click(selector, timeout=config.BROWSER_TIMEOUT)
        await self._wait_for_stability()

    async def type_text(self, selector: str, text: str, clear: bool = True) -> None:
        """Type text into an element."""
        if clear:
            await self.page.fill(selector, text)
        else:
            await self.page.type(selector, text)
        await asyncio.sleep(config.ACTION_DELAY)

    async def press_key(self, keys: str) -> None:
        """Press keyboard keys."""
        await self.page.keyboard.press(keys)
        await asyncio.sleep(config.ACTION_DELAY)

    async def scroll(self, amount: int) -> None:
        """Scroll the page by amount (positive = down, negative = up)."""
        await self.page.evaluate(f"window.scrollBy(0, {amount})")
        await asyncio.sleep(config.ACTION_DELAY)

    async def hover(self, selector: str) -> None:
        """Hover over an element."""
        await self.page.hover(selector)
        await asyncio.sleep(config.ACTION_DELAY)

    async def go_back(self) -> None:
        """Navigate back."""
        await self.page.go_back()
        await self._wait_for_stability()

    async def take_screenshot(self, path: Path, full_page: bool = False) -> None:
        """Take a screenshot."""
        await self.page.screenshot(path=str(path), full_page=full_page)

    async def get_visible_text(self, max_length: int = 2000) -> str:
        """Get visible text content from the page."""
        text = await self.page.evaluate("""
            () => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: (node) => {
                            const parent = node.parentElement;
                            if (!parent) return NodeFilter.FILTER_REJECT;

                            const style = window.getComputedStyle(parent);
                            if (style.display === 'none' || style.visibility === 'hidden') {
                                return NodeFilter.FILTER_REJECT;
                            }

                            const tag = parent.tagName.toLowerCase();
                            if (['script', 'style', 'noscript'].includes(tag)) {
                                return NodeFilter.FILTER_REJECT;
                            }

                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );

                const texts = [];
                let node;
                while (node = walker.nextNode()) {
                    const text = node.textContent.trim();
                    if (text) texts.push(text);
                }
                return texts.join(' ');
            }
        """)
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text

    async def get_page_title(self) -> str:
        """Get page title."""
        return await self.page.title()

    async def query_interactive_elements(
        self,
        query: str = "",
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """
        Query interactive elements on the page.

        Returns elements matching the query with their properties and
        dynamically generated selectors.
        """
        # JavaScript to collect interactive elements
        elements_data = await self.page.evaluate("""
            (args) => {
                const { query, limit } = args;
                const queryLower = query.toLowerCase();

                // Transliteration map for common brand searches
                const translitMap = {
                    'milka': 'милка',
                    'милка': 'milka',
                    'oreo': 'орео',
                    'snickers': 'сникерс',
                    'mars': 'марс',
                    'twix': 'твикс',
                    'bounty': 'баунти',
                    'kitkat': 'киткат',
                    'nestle': 'нестле',
                };
                const queryAlt = translitMap[queryLower] || '';

                // Selectors for interactive elements (including product cards)
                const interactiveSelectors = [
                    'a[href]',
                    'button',
                    'input',
                    'textarea',
                    'select',
                    '[role="button"]',
                    '[role="link"]',
                    '[role="menuitem"]',
                    '[role="tab"]',
                    '[role="checkbox"]',
                    '[role="radio"]',
                    '[onclick]',
                    '[tabindex]:not([tabindex="-1"])',
                    // Product cards - common patterns
                    '[class*="product"]',
                    '[class*="Product"]',
                    '[class*="card"]',
                    '[class*="Card"]',
                    '[class*="item"]',
                    '[class*="Item"]',
                    '[data-product]',
                    '[data-item]',
                    'article',
                ];

                const allElements = document.querySelectorAll(interactiveSelectors.join(','));
                const candidates = [];

                // DEBUG: Count elements by selector type
                const debugInfo = {
                    totalElements: allElements.length,
                    selectorCounts: {},
                    textMatches: [],
                    query: queryLower,
                    queryAlt: queryAlt,
                };
                for (const sel of interactiveSelectors) {
                    const count = document.querySelectorAll(sel).length;
                    if (count > 0) debugInfo.selectorCounts[sel] = count;
                }

                // Debug: find elements with query text
                if (queryLower) {
                    let matchCount = 0;
                    for (const el of allElements) {
                        const text = (el.innerText || '').toLowerCase();
                        if (text.includes(queryLower) || (queryAlt && text.includes(queryAlt))) {
                            matchCount++;
                            if (debugInfo.textMatches.length < 5) {
                                debugInfo.textMatches.push({
                                    tag: el.tagName,
                                    text: text.slice(0, 50),
                                    hasQuery: text.includes(queryLower),
                                    hasAlt: queryAlt ? text.includes(queryAlt) : false,
                                });
                            }
                        }
                    }
                    debugInfo.textMatchCount = matchCount;
                }

                for (const el of allElements) {
                    // Check visibility
                    const rect = el.getBoundingClientRect();
                    if (rect.width === 0 || rect.height === 0) continue;

                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') continue;
                    if (parseFloat(style.opacity) < 0.1) continue;

                    // Collect text content
                    const innerText = (el.innerText || '').trim().slice(0, 200);
                    const ariaLabel = el.getAttribute('aria-label') || '';
                    const placeholder = el.getAttribute('placeholder') || '';
                    const title = el.getAttribute('title') || '';
                    const name = el.getAttribute('name') || '';
                    const value = el.value || '';
                    const alt = el.getAttribute('alt') || '';

                    // Combine searchable text
                    const searchText = [
                        innerText, ariaLabel, placeholder, title, name, value, alt
                    ].join(' ').toLowerCase();

                    // Score match (check both original query and transliteration)
                    let score = 0;
                    if (queryLower) {
                        const matchesQuery = searchText.includes(queryLower);
                        const matchesAlt = queryAlt && searchText.includes(queryAlt);

                        if (matchesQuery || matchesAlt) {
                            score = 1;
                            // Boost exact matches
                            const textLower = innerText.toLowerCase();
                            const ariaLower = ariaLabel.toLowerCase();
                            if (textLower === queryLower || ariaLower === queryLower ||
                                textLower === queryAlt || ariaLower === queryAlt) {
                                score = 2;
                            }
                        }
                    } else {
                        score = 1; // No query = return all
                    }

                    if (score === 0 && queryLower) continue;

                    // Get role
                    let role = el.getAttribute('role') || el.tagName.toLowerCase();
                    if (el.tagName === 'INPUT') {
                        role = `input[${el.type || 'text'}]`;
                    }

                    // Collect attributes for selector generation
                    const attributes = {};
                    const attrNames = [
                        'data-testid', 'data-qa', 'data-test',
                        'aria-label', 'name', 'type', 'href'
                    ];
                    for (const attr of attrNames) {
                        const val = el.getAttribute(attr);
                        if (val) attributes[attr] = val;
                    }

                    // Build CSS path
                    const getPath = (element, maxDepth = 4) => {
                        const path = [];
                        let current = element;
                        let depth = 0;

                        while (current && current !== document.body && depth < maxDepth) {
                            let selector = current.tagName.toLowerCase();

                            // Add first class if meaningful
                            if (current.classList.length > 0) {
                                const cls = Array.from(current.classList).find(c =>
                                    c.length > 2 && c.length < 30 &&
                                    !c.startsWith('css-') && !c.startsWith('sc-')
                                );
                                if (cls) selector += '.' + cls;
                            }

                            // Add nth-of-type if needed
                            const parent = current.parentElement;
                            if (parent) {
                                const siblings = Array.from(parent.children).filter(
                                    c => c.tagName === current.tagName
                                );
                                if (siblings.length > 1) {
                                    const index = siblings.indexOf(current) + 1;
                                    selector += `:nth-of-type(${index})`;
                                }
                            }

                            path.unshift(selector);
                            current = parent;
                            depth++;
                        }

                        return path.join(' > ');
                    };

                    candidates.push({
                        tag: el.tagName.toLowerCase(),
                        role: role,
                        text: innerText.slice(0, 100),
                        ariaLabel: ariaLabel,
                        placeholder: placeholder,
                        name: name,
                        id: el.id || '',
                        attributes: attributes,
                        bbox: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height),
                        },
                        cssPath: getPath(el),
                        score: score,
                        inViewport: (
                            rect.top >= 0 &&
                            rect.left >= 0 &&
                            rect.bottom <= window.innerHeight &&
                            rect.right <= window.innerWidth
                        ),
                    });
                }

                // Sort by score (descending) and viewport visibility
                candidates.sort((a, b) => {
                    if (b.score !== a.score) return b.score - a.score;
                    if (a.inViewport !== b.inViewport) return a.inViewport ? -1 : 1;
                    return a.bbox.y - b.bbox.y; // Top to bottom
                });

                return {
                    candidates: candidates.slice(0, limit),
                    debug: debugInfo,
                };
            }
        """, {"query": query, "limit": limit})

        # Extract debug info if present
        if isinstance(elements_data, dict) and "debug" in elements_data:
            debug_info = elements_data.get("debug", {})
            elements_data = elements_data.get("candidates", [])
            # Print debug info
            import os
            if os.environ.get("DEBUG_SELECTORS", "0") == "1":
                print(f"  [JS DEBUG] Total elements: {debug_info.get('totalElements', '?')}")
                print(f"  [JS DEBUG] Query: '{debug_info.get('query', '')}', Alt: '{debug_info.get('queryAlt', '')}'")
                print(f"  [JS DEBUG] Text match count: {debug_info.get('textMatchCount', '?')}")
                if debug_info.get('textMatches'):
                    print(f"  [JS DEBUG] Sample matches:")
                    for m in debug_info.get('textMatches', []):
                        print(f"    - <{m.get('tag')}> '{m.get('text')}' hasQuery={m.get('hasQuery')}")

        # Generate unique selectors for each element
        from src.browser.selectors import generate_unique_selector

        for elem in elements_data:
            elem["selector"] = generate_unique_selector(elem)

        return elements_data

    async def close_popups(self) -> bool:
        """Try to close common popups/modals. Returns True if something was closed."""
        closed = False

        # Common close button patterns (searched dynamically)
        close_candidates = await self.query_interactive_elements("close", limit=5)
        close_candidates += await self.query_interactive_elements("dismiss", limit=3)
        close_candidates += await self.query_interactive_elements("cancel", limit=3)

        for candidate in close_candidates:
            # Check if it looks like a close button
            text_lower = (candidate.get("text", "") + candidate.get("ariaLabel", "")).lower()
            close_keywords = ["close", "dismiss", "cancel", "x", "закрыть", "отмена"]
            if any(kw in text_lower for kw in close_keywords):
                try:
                    await self.page.click(candidate["selector"], timeout=2000)
                    closed = True
                    await asyncio.sleep(0.5)
                except Exception:
                    continue

        # Try pressing Escape
        try:
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.3)
        except Exception:
            pass

        return closed

    async def _wait_for_stability(self, timeout: float = 2.0) -> None:
        """Wait for page to stabilize after navigation/action."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
        except Exception:
            pass

        # Brief pause for dynamic content
        await asyncio.sleep(config.ACTION_DELAY)
