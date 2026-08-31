"""
Core orchestrator — coordinates Redis, Browser, Platform, Dedup, Kafka.

Does NOT contain platform selectors or Kafka offset commits.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from core.config import settings
from core.kafka_producer.producer import KafkaProducer
from core.models import CleanPost, CrawlOutcome, CrawlTask
from core.redis_dedup.store import RedisStateStore
from core.resilience.browser_manager import BrowserManager
from core.resilience.errors import (
    BlockDetectedError,
    CrawlError,
    PublishError,
    RedisUnavailableError,
)
from platforms.reddit.crawler import RedditCrawler


logger = logging.getLogger("crawler.orchestrator")


# ============================================================
# VIETNAM TIMEZONE
# ============================================================

VN_TZ = timezone(timedelta(hours=7))


def now_vn() -> datetime:
    """
    Current time in Vietnam timezone (UTC+7).
    """
    return datetime.now(VN_TZ)


def parse_baseline_since(raw: str) -> datetime:
    """
    Parse baseline_since.

    Rules:
    - 2026-08-31T13:00:00+07:00
        -> Vietnam time
    - 2026-08-31T06:00:00Z
        -> UTC, then converted to Vietnam time
    - 2026-08-31T13:00:00
        -> assumed to be Vietnam time
    """

    value = raw.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    dt = datetime.fromisoformat(value)

    # No timezone supplied:
    # IMPORTANT: interpret it as Vietnam time.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=VN_TZ)

    return dt.astimezone(VN_TZ)


def validate_baseline_since(raw: str) -> tuple[str, Optional[str]]:
    """
    Validate baseline_since using Vietnam time.

    The crawler accepts only data within
    MAX_INITIAL_LOOKBACK_HOURS from current time.

    Returned ISO timestamp always contains +07:00.
    """

    try:
        dt = parse_baseline_since(raw)

    except Exception as e:
        return (
            raw,
            f"invalid baseline_since ISO-8601: {e}",
        )

    now = now_vn()

    # Future timestamp
    if dt > now:
        return (
            raw,
            (
                "since cannot be later than current time "
                f"(now VN: {now.isoformat()})"
            ),
        )

    earliest = (
        now
        - timedelta(
            hours=settings.max_initial_lookback_hours
        )
    )

    # Too old
    if dt < earliest:

        if settings.since_policy == "clamp":
            logger.warning(
                "baseline_since=%s is older than allowed. "
                "Clamping to %s",
                dt.isoformat(),
                earliest.isoformat(),
            )

            return earliest.isoformat(), None

        return (
            raw,
            (
                "since is older than "
                "MAX_INITIAL_LOOKBACK_HOURS="
                f"{settings.max_initial_lookback_hours} "
                f"(earliest allowed VN: {earliest.isoformat()})"
            ),
        )

    return dt.isoformat(), None


class Orchestrator:

    def __init__(
        self,
        *,
        redis: RedisStateStore,
        browser: BrowserManager,
        producer: KafkaProducer,
        platform: str = "reddit",
    ) -> None:

        self.redis = redis
        self.browser = browser
        self.producer = producer
        self.platform = platform
        self.reddit = RedditCrawler()

    async def process_task(
        self,
        task: CrawlTask,
    ) -> CrawlOutcome:

        platform = task.platform or self.platform
        keyword = task.keyword

        # ========================================================
        # BASELINE TIME
        # ========================================================

        since_iso, since_err = validate_baseline_since(
            task.baseline_since
        )

        if since_err:
            return CrawlOutcome(
                success=False,
                platform=platform,
                keyword=keyword,
                baseline_since=task.baseline_since,
                error=since_err,
            )

        # ========================================================
        # REDIS CHECKPOINT
        # ========================================================

        try:
            last_post_id = await self.redis.get_checkpoint(
                platform,
                keyword,
            )

        except RedisUnavailableError as e:
            return CrawlOutcome(
                success=False,
                platform=platform,
                keyword=keyword,
                baseline_since=since_iso,
                error=str(e),
            )

        crawl_type = (
            "incremental"
            if last_post_id
            else "initial"
        )

        # Current time in Vietnam
        until = now_vn().isoformat()

        logger.info(
            "Task platform=%s keyword=%r "
            "type=%s checkpoint=%s since=%s until=%s",
            platform,
            keyword,
            crawl_type,
            last_post_id,
            since_iso,
            until,
        )

        context = None
        page = None

        # ========================================================
        # BROWSER + PLATFORM CRAWLER
        # ========================================================

        try:

            context, page = (
                await self.browser.get_stealth_page()
            )

            if platform != "reddit":
                raise CrawlError(
                    f"Unsupported platform: {platform}"
                )

            raw_posts = await self.reddit.crawl(
                page,
                keyword=keyword,
                baseline_since=since_iso,
                last_post_id=last_post_id,
            )

        except BlockDetectedError as e:

            return CrawlOutcome(
                success=False,
                platform=platform,
                keyword=keyword,
                crawl_type=crawl_type,
                baseline_since=since_iso,
                until=until,
                checkpoint_found=bool(last_post_id),
                error=str(e),
            )

        except Exception as e:

            logger.exception("Crawl failed")

            return CrawlOutcome(
                success=False,
                platform=platform,
                keyword=keyword,
                crawl_type=crawl_type,
                baseline_since=since_iso,
                until=until,
                checkpoint_found=bool(last_post_id),
                error=str(e),
            )

        finally:

            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass

            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

        # ========================================================
        # DEDUP + CLEAN
        # ========================================================

        clean: List[CleanPost] = []

        fetched_at = now_vn().isoformat()

        for raw in raw_posts:

            pid = raw.get("post_id")

            if not pid:
                continue

            try:

                if await self.redis.is_duplicate(
                    platform,
                    pid,
                ):
                    continue

            except RedisUnavailableError as e:

                return CrawlOutcome(
                    success=False,
                    platform=platform,
                    keyword=keyword,
                    crawl_type=crawl_type,
                    baseline_since=since_iso,
                    until=until,
                    checkpoint_found=bool(last_post_id),
                    error=str(e),
                )

            clean.append(
                CleanPost(
                    post_id=pid,
                    platform=platform,
                    keyword=keyword,
                    title=raw.get("title") or "",
                    content=raw.get("content") or "",
                    author=raw.get("author") or "[unknown]",
                    created_at=raw.get("created_at"),
                    url=raw.get("url") or "",
                    permalink=raw.get("permalink") or "",
                    score=raw.get("score") or 0,
                    num_comments=raw.get("num_comments") or 0,
                    fetched_at=fetched_at,
                )
            )

        # ========================================================
        # PUBLISH
        # ========================================================

        try:

            if clean:

                await self.producer.publish_posts(
                    keyword,
                    clean,
                )

                for p in clean:
                    await self.redis.mark_seen(
                        platform,
                        p.post_id,
                    )

        except (
            PublishError,
            RedisUnavailableError,
        ) as e:

            return CrawlOutcome(
                success=False,
                platform=platform,
                keyword=keyword,
                crawl_type=crawl_type,
                baseline_since=since_iso,
                until=until,
                checkpoint_found=bool(last_post_id),
                count=len(clean),
                error=str(e),
            )

        # ========================================================
        # CHECKPOINT
        # ========================================================

        new_cp: Optional[str] = (
            clean[0].post_id
            if clean
            else None
        )

        checkpoint_updated = False

        if new_cp:

            try:

                await self.redis.set_checkpoint(
                    platform,
                    keyword,
                    new_cp,
                )

                checkpoint_updated = True

            except RedisUnavailableError as e:

                return CrawlOutcome(
                    success=False,
                    platform=platform,
                    keyword=keyword,
                    crawl_type=crawl_type,
                    baseline_since=since_iso,
                    until=until,
                    checkpoint_found=bool(last_post_id),
                    count=len(clean),
                    posts=[
                        p.to_dict()
                        for p in clean
                    ],
                    error=(
                        "checkpoint save failed "
                        f"after publish: {e}"
                    ),
                )

        # ========================================================
        # SUCCESS
        # ========================================================

        return CrawlOutcome(
            success=True,
            platform=platform,
            keyword=keyword,
            crawl_type=crawl_type,
            baseline_since=since_iso,
            until=until,
            checkpoint_found=bool(last_post_id),
            checkpoint_updated=checkpoint_updated,
            last_post_id=new_cp or last_post_id,
            count=len(clean),
            posts=[
                p.to_dict()
                for p in clean
            ],
        )