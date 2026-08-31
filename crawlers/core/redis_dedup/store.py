"""Redis checkpoint + seen-set (double-layer dedup)."""

from __future__ import annotations

import logging
import re
from typing import Optional

import redis.asyncio as redis

from core.config import settings
from core.resilience.errors import RedisUnavailableError

logger = logging.getLogger("crawler.redis")


def normalize_keyword(keyword: str) -> str:
    k = keyword.strip().lower()
    k = re.sub(r"\s+", "_", k)
    k = re.sub(r"[^\w\-]", "", k)
    return k[:120] or "unknown"


class RedisStateStore:
    def __init__(self, url: Optional[str] = None) -> None:
        self._url = url or settings.redis_url
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        try:
            self._client = redis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            await self._client.ping()
            logger.info("Redis connected %s", self._url)
        except Exception as e:
            raise RedisUnavailableError(f"Redis connect failed: {e}") from e

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _require(self) -> redis.Redis:
        if self._client is None:
            raise RedisUnavailableError("Redis not connected")
        return self._client

    def checkpoint_key(self, platform: str, keyword: str) -> str:
        return (
            f"{settings.redis_checkpoint_prefix}:"
            f"{platform}:{normalize_keyword(keyword)}"
        )

    def seen_key(self, platform: str, post_id: str) -> str:
        return f"{settings.redis_seen_prefix}:{platform}:{post_id}"

    async def get_checkpoint(self, platform: str, keyword: str) -> Optional[str]:
        client = self._require()
        try:
            value = await client.get(self.checkpoint_key(platform, keyword))
            return value if value else None
        except Exception as e:
            raise RedisUnavailableError(f"get_checkpoint failed: {e}") from e

    async def set_checkpoint(
        self, platform: str, keyword: str, last_post_id: str
    ) -> None:
        if not last_post_id:
            raise ValueError("last_post_id must not be empty")
        client = self._require()
        try:
            key = self.checkpoint_key(platform, keyword)
            await client.set(key, last_post_id)
            logger.info("Checkpoint set %s -> %s", key, last_post_id)
        except Exception as e:
            raise RedisUnavailableError(f"set_checkpoint failed: {e}") from e

    async def is_duplicate(self, platform: str, post_id: str) -> bool:
        client = self._require()
        try:
            return bool(await client.exists(self.seen_key(platform, post_id)))
        except Exception as e:
            raise RedisUnavailableError(f"is_duplicate failed: {e}") from e

    async def mark_seen(self, platform: str, post_id: str) -> None:
        client = self._require()
        try:
            await client.set(
                self.seen_key(platform, post_id),
                "1",
                ex=settings.redis_seen_ttl_seconds,
            )
        except Exception as e:
            raise RedisUnavailableError(f"mark_seen failed: {e}") from e