"""Singleton Playwright + Chromium manager."""

from __future__ import annotations

import logging
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from core.config import settings
from core.resilience.errors import BrowserError

logger = logging.getLogger("crawler.resilience")

_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""


class BrowserManager:
    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        if self._browser is not None:
            return
        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.browser_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                ],
            )
            logger.info("Chromium started headless=%s", settings.browser_headless)
        except Exception as e:
            raise BrowserError(f"Failed to start Chromium: {e}") from e

    async def stop(self) -> None:
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning("Browser close error: %s", e)
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning("Playwright stop error: %s", e)
            self._playwright = None
        logger.info("BrowserManager stopped")

    async def get_stealth_page(self) -> tuple[BrowserContext, Page]:
        if self._browser is None:
            raise BrowserError("Browser not started")

        try:
            context = await self._browser.new_context(
                user_agent=settings.user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="Asia/Ho_Chi_Minh",
                java_script_enabled=True,
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/avif,image/webp,"
                        "image/apng,*/*;q=0.8"
                    ),
                    "Upgrade-Insecure-Requests": "1",
                },
            )

            await context.add_init_script(_STEALTH_JS)

            page = await context.new_page()
            page.set_default_timeout(settings.navigation_timeout_ms)

            logger.info(
                "Stealth page created timezone=%s locale=%s",
                "Asia/Ho_Chi_Minh",
                "en-US",
            )

            return context, page

        except Exception as e:
            raise BrowserError(
                f"Failed to create stealth page: {e}"
            ) from e