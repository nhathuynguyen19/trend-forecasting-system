"""Kafka task consumer for crawl-tasks.{platform}."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Optional

from aiokafka import AIOKafkaConsumer

from core.config import settings
from core.models import CrawlTask

logger = logging.getLogger("crawler.kafka.consumer")


def parse_task_message(
    raw: bytes | str,
    *,
    platform: str,
    key: Optional[bytes | str] = None,
) -> CrawlTask:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)

    if isinstance(data, dict) and isinstance(data.get("value"), dict):
        payload = data["value"]
        platform = data.get("platform") or platform
    else:
        payload = data if isinstance(data, dict) else {}

    if isinstance(platform, str) and platform.startswith("crawl-tasks."):
        platform = platform.split(".", 1)[-1]

    keyword = (payload.get("keyword") or "").strip()
    if not keyword and key is not None:
        keyword = (key.decode("utf-8") if isinstance(key, bytes) else str(key)).strip()

    baseline = payload.get("baseline_since") or payload.get("since")
    if not baseline:
        raise ValueError("missing baseline_since/since")
    if not keyword:
        raise ValueError("keyword must not be empty")

    return CrawlTask(platform=platform, keyword=keyword, baseline_since=str(baseline))


class KafkaTaskConsumer:
    def __init__(self, platform: Optional[str] = None) -> None:
        self._platform = platform or settings.platform
        self._consumer: Optional[AIOKafkaConsumer] = None

    @property
    def topic(self) -> str:
        return f"{settings.kafka_task_topic_prefix}.{self._platform}"

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            max_poll_interval_ms=settings.kafka_max_poll_interval_ms,
        )
        await self._consumer.start()
        logger.info(
            "Consumer started topic=%s group=%s max_poll_interval_ms=%s",
            self.topic,
            settings.kafka_group_id,
            settings.kafka_max_poll_interval_ms,
        )

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def messages(self) -> AsyncIterator[tuple[CrawlTask, Any]]:
        assert self._consumer is not None
        async for record in self._consumer:
            try:
                task = parse_task_message(
                    record.value,
                    platform=self._platform,
                    key=record.key,
                )
                yield task, record
            except Exception as e:
                logger.error("Invalid task message skipped: %s raw=%r", e, record.value)
                await self._consumer.commit()
                continue

    async def commit(self) -> None:
        assert self._consumer is not None
        await self._consumer.commit()