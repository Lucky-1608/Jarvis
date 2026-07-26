"""
Jarvis OS — Browser Engine.

Manages the Playwright lifecycle for browser automation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Global instances to keep the browser alive across calls
_playwright = None
_browser = None
_context = None
_page = None

class BrowserEngine:
    """
    Manages a single persistent browser session.
    """

    @classmethod
    async def get_page(cls) -> "Page":
        """Get the active Playwright page, initializing if necessary."""
        global _playwright, _browser, _context, _page

        try:
            from playwright.async_api import async_playwright, Page
        except ImportError:
            raise RuntimeError(
                "playwright is required for browser automation. "
                "Install with: pip install 'jarvis-os[automation]'"
            )

        if _page is not None and not _page.is_closed():
            return _page

        if _playwright is None:
            logger.info("browser.starting_playwright")
            _playwright = await async_playwright().start()

        if _browser is None:
            logger.info("browser.launching_chromium")
            _browser = await _playwright.chromium.launch(headless=False)

        if _context is None:
            _context = await _browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) JarvisOS/0.1"
            )

        _page = await _context.new_page()
        logger.info("browser.page_created")
        return _page

    @classmethod
    async def navigate(cls, url: str) -> dict[str, Any]:
        """Navigate to a specific URL."""
        page = await cls.get_page()
        logger.info("browser.navigating", url=url)
        response = await page.goto(url, wait_until="domcontentloaded")
        
        return {
            "url": page.url,
            "title": await page.title(),
            "status": response.status if response else None,
        }

    @classmethod
    async def click(cls, selector: str) -> dict[str, Any]:
        """Click on an element specified by a selector."""
        page = await cls.get_page()
        logger.info("browser.clicking", selector=selector)
        await page.click(selector)
        return {"action": "click", "selector": selector, "status": "success"}

    @classmethod
    async def type_text(cls, selector: str, text: str) -> dict[str, Any]:
        """Type text into an element specified by a selector."""
        page = await cls.get_page()
        logger.info("browser.typing", selector=selector)
        await page.fill(selector, text)
        return {"action": "type", "selector": selector, "status": "success"}

    @classmethod
    async def extract_content(cls, format: str = "text") -> dict[str, Any]:
        """Extract text or HTML content from the current page."""
        page = await cls.get_page()
        
        if format == "html":
            content = await page.content()
        else:
            # Extract plain text from body
            content = await page.evaluate("document.body.innerText")
            
        return {
            "url": page.url,
            "title": await page.title(),
            "content": content,
            "format": format
        }

    @classmethod
    async def shutdown(cls) -> None:
        """Close the browser and Playwright instances."""
        global _playwright, _browser, _context, _page
        
        logger.info("browser.shutting_down")
        if _page:
            await _page.close()
            _page = None
        if _context:
            await _context.close()
            _context = None
        if _browser:
            await _browser.close()
            _browser = None
        if _playwright:
            await _playwright.stop()
            _playwright = None
