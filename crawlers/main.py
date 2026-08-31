"""
Crawler Worker entrypoint.

Lifecycle:
  Startup → Config → Redis → Kafka Producer → Browser → Kafka Consumer
  → process tasks → Graceful shutdown on SIGTERM/SIGINT
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

from core.config import settings
from core.kafka_consumer.consumer import KafkaTaskConsumer
from core.kafka_producer.producer import KafkaProducer
from core.orchestrator import Orchestrator
from core.redis_dedup.store import RedisStateStore
from core.resilience.browser_manager import BrowserManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("crawler.main")


class Worker:
    def __init__(self) -> None:
        self.redis = RedisStateStore()
        self.browser = BrowserManager()
        self.producer = KafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
        self.consumer = KafkaTaskConsumer(platform=settings.platform)
        self.orchestrator: Orchestrator | None = None
        self._stopping = False

    async def start(self) -> None:
        await self.redis.connect()
        await self.producer.start()
        await self.browser.start()
        self.orchestrator = Orchestrator(
            redis=self.redis,
            browser=self.browser,
            producer=self.producer,
            platform=settings.platform,
        )
        await self.consumer.start()
        logger.info(
            "Worker ready platform=%s topic=%s",
            settings.platform,
            self.consumer.topic,
        )

    async def stop(self) -> None:
        self._stopping = True
        await self.consumer.stop()
        await self.browser.stop()
        await self.producer.stop()
        await self.redis.close()
        logger.info("Worker stopped")

    async def run(self) -> None:
        await self.start()
        assert self.orchestrator is not None
        try:
            async for task, _record in self.consumer.messages():
                if self._stopping:
                    break
                logger.info(
                    "Received task keyword=%r baseline_since=%s",
                    task.keyword,
                    task.baseline_since,
                )
                try:
                    outcome = await self.orchestrator.process_task(task)
                    if outcome.success:
                        await self.consumer.commit()
                        logger.info(
                            "SUCCESS keyword=%r type=%s count=%s checkpoint_updated=%s",
                            outcome.keyword,
                            outcome.crawl_type,
                            outcome.count,
                            outcome.checkpoint_updated,
                        )
                    else:
                        logger.error(
                            "FAIL keyword=%r error=%s (offset NOT committed)",
                            task.keyword,
                            outcome.error,
                        )
                except Exception:
                    logger.exception(
                        "Unhandled task error keyword=%r (offset NOT committed)",
                        task.keyword,
                    )
        finally:
            await self.stop()


def main() -> None:
    worker = Worker()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _handle_signal() -> None:
        logger.info("Signal received — graceful shutdown")
        worker._stopping = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(worker.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()