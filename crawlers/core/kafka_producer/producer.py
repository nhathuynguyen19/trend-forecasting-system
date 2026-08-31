from __future__ import annotations

import asyncio
import json
import logging
from typing import Iterable

from aiokafka import AIOKafkaProducer

from core.models import CleanPost
from core.resilience.errors import PublishError
from core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    """Single raw-data producer for social.posts.raw.

    The producer is created inside ``start()`` so aiokafka is initialized
    while an asyncio event loop is already running.
    """

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        max_retries = 10

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Connecting to Kafka %s (attempt %s/%s)",
                    self.bootstrap_servers,
                    attempt,
                    max_retries,
                )

                # aiokafka must be constructed inside an async context.
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    acks="all",
                )
                await self._producer.start()

                logger.info(
                    "Kafka connected successfully: %s",
                    self.bootstrap_servers,
                )
                return

            except Exception as e:
                logger.warning("Kafka connection failed: %s", e)

                if self._producer is not None:
                    try:
                        await self._producer.stop()
                    except Exception:
                        pass
                    self._producer = None

                if attempt == max_retries:
                    raise

                wait_time = min(attempt * 2, 10)
                logger.info("Retrying Kafka connection in %s seconds...", wait_time)
                await asyncio.sleep(wait_time)

    async def publish_posts(
        self,
        keyword: str,
        posts: Iterable[CleanPost],
    ) -> None:
        if self._producer is None:
            raise PublishError("Kafka producer is not started")

        topic = settings.kafka_result_topic
        sent = 0

        try:
            for post in posts:
                payload = post.to_dict()
                value = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                key = keyword.encode("utf-8")

                # send_and_wait makes a publish failure visible to Core, so
                # the Kafka task offset is not committed on failure.
                await self._producer.send_and_wait(
                    topic,
                    key=key,
                    value=value,
                )
                sent += 1

            logger.info(
                "Published %d posts topic=%s keyword=%r",
                sent,
                topic,
                keyword,
            )
        except Exception as e:
            raise PublishError(
                f"Kafka publish failed topic={topic!r} keyword={keyword!r}: {e}"
            ) from e

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
