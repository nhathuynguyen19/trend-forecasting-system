"""Typed errors for crawler resilience layer."""

from __future__ import annotations


class CrawlError(Exception):
    """Base crawl error."""


class BrowserError(CrawlError):
    """Browser lifecycle / Playwright failures."""


class NavigationError(CrawlError):
    """Page navigation failures."""


class BlockDetectedError(CrawlError):
    """Captcha / challenge / access-denied page detected (no bypass)."""


class PublishError(CrawlError):
    """Kafka publish failure."""


class RedisUnavailableError(CrawlError):
    """Redis connection or operation failure — hard stop."""