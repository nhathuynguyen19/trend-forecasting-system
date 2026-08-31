"""Reddit crawler — one task -> many posts (JSON-first)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from core.config import settings
from core.resilience.delays import human_delay
from core.resilience.errors import BlockDetectedError, NavigationError
from platforms.reddit.parser import RedditParser
from platforms.reddit import selectors as sel

logger = logging.getLogger("crawler.reddit")

BLOCK_MARKERS = (
    "you've been blocked by network security",
    "please complete the security check",
    "verify you are a human",
    "are you a robot",
    "access denied",
    "recaptcha",
    "welcome to reddit",
    "reason=lor2",
)


def build_search_json_url(
    keyword: str,
    *,
    after: Optional[str] = None,
    limit: int = 100,
) -> str:
    params: Dict[str, str] = {
        "q": keyword,
        "sort": "new",
        "t": "all",
        "limit": str(min(limit, 100)),
        "raw_json": "1",
    }
    if after:
        params["after"] = after
    return f"https://old.reddit.com/search.json?{urlencode(params)}"


def build_search_html_url(keyword: str) -> str:
    params = {
        "q": keyword,
        "sort": "new",
        "t": "all",
        "limit": "100",
    }
    return f"https://old.reddit.com/search/?{urlencode(params)}"


def _parse_iso(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _json_child_to_post(child: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map Reddit listing JSON child -> raw post dict (same shape as parser)."""
    try:
        data = child.get("data") or {}
        post_id = (data.get("id") or "").strip()
        if not post_id:
            return None

        created_utc = data.get("created_utc")
        created_at = None
        if created_utc is not None:
            try:
                created_at = datetime.fromtimestamp(
                    float(created_utc), tz=timezone.utc
                ).isoformat()
            except (TypeError, ValueError, OSError):
                created_at = None

        permalink = data.get("permalink") or ""
        if permalink and not permalink.startswith("http"):
            permalink = f"https://www.reddit.com{permalink}"

        url = data.get("url") or permalink

        return {
            "post_id": post_id,
            "title": (data.get("title") or "").strip(),
            "content": (data.get("selftext") or "").strip(),
            "author": data.get("author") or "[deleted]",
            "score": data.get("score"),
            "num_comments": int(data.get("num_comments") or 0),
            "url": url or "",
            "permalink": permalink or "",
            "created_at": created_at,
        }
    except Exception as e:
        logger.warning("JSON child parse error: %s", e)
        return None


async def _detect_block(page: Page) -> Optional[str]:
    try:
        current_url = (page.url or "").lower()
        title = (await page.title() or "").lower()

        if "/login" in current_url or "reason=lor2" in current_url:
            return "reddit_login_required"
        if "welcome to reddit" in title:
            return "reddit_welcome_login_wall"

        html = (await page.content())[:40000].lower()
        body = (
            await page.evaluate(
                "() => document.body ? document.body.innerText.toLowerCase() : ''"
            )
        )[:15000]
        combined = f"{title} {body} {html} {current_url}"
        for marker in BLOCK_MARKERS:
            if marker in combined:
                return "block_or_captcha"
        if len(body.strip()) < 80 and "thing" not in html and "sitetable" not in html:
            if "children" not in html and '"kind"' not in html:
                return "empty_or_challenge_page"
    except Exception as e:
        logger.warning("Block detection error: %s", e)
        return None
    return None


class RedditCrawler:
    def __init__(self) -> None:
        self.parser = RedditParser()

    async def crawl(
        self,
        page: Page,
        *,
        keyword: str,
        baseline_since: str,
        last_post_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        One task -> many posts.

        Primary: search.json + after pagination
        Fallback: HTML listing + next-button
        """
        since_dt = _parse_iso(baseline_since)
        seen: Set[str] = set()
        collected: List[Dict] = []

        logger.info(
            "Start Reddit crawl keyword=%r baseline_since=%s last_post_id=%s",
            keyword,
            baseline_since,
            last_post_id,
        )

        # ---------- PRIMARY: JSON API ----------
        try:
            posts, stop_reason = await self._crawl_json(
                page,
                keyword=keyword,
                since_dt=since_dt,
                last_post_id=last_post_id,
                seen=seen,
                collected=collected,
            )
            logger.info(
                "JSON crawl done keyword=%r total=%d stop=%s",
                keyword,
                len(posts),
                stop_reason,
            )
            if posts:
                return posts
            # empty but clean stop (baseline / checkpoint) -> return empty
            if stop_reason in ("baseline", "checkpoint", "no_after", "max_pages"):
                return posts
        except BlockDetectedError:
            raise
        except NavigationError:
            raise
        except Exception as e:
            logger.warning("JSON crawl failed, fallback HTML: %s", e)

        # ---------- FALLBACK: HTML ----------
        return await self._crawl_html(
            page,
            keyword=keyword,
            since_dt=since_dt,
            last_post_id=last_post_id,
            seen=seen,
            collected=collected,
        )

    # ==================================================================
    # JSON path
    # ==================================================================
    async def _crawl_json(
        self,
        page: Page,
        *,
        keyword: str,
        since_dt: datetime,
        last_post_id: Optional[str],
        seen: Set[str],
        collected: List[Dict],
    ) -> Tuple[List[Dict], str]:
        after: Optional[str] = None
        pages = 0
        no_progress = 0
        stop_reason = "max_pages"

        while pages < settings.max_pages_per_task:
            url = build_search_json_url(keyword, after=after, limit=100)
            logger.info("JSON GET page=%d url=%s", pages + 1, url)

            try:
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.navigation_timeout_ms,
                )
            except PlaywrightTimeout as e:
                raise NavigationError(f"JSON navigation timeout: {e}") from e

            status = response.status if response else 0
            final_url = (page.url or "").lower()
            logger.info("JSON HTTP status=%s final_url=%s", status, page.url)

            if "/login" in final_url or "reason=lor2" in final_url:
                raise BlockDetectedError(
                    f"Reddit login wall on JSON: url={page.url}"
                )

            if status >= 400:
                raise NavigationError(f"JSON HTTP {status} for {url}")

            # Body must be JSON
            try:
                text = await page.inner_text("body")
            except Exception:
                text = await page.content()

            text = (text or "").strip()
            if not text.startswith("{") and not text.startswith("["):
                blocked = await _detect_block(page)
                raise BlockDetectedError(
                    f"JSON endpoint returned non-JSON "
                    f"(block={blocked}) url={page.url}"
                )

            try:
                payload = json.loads(text)
            except json.JSONDecodeError as e:
                raise BlockDetectedError(
                    f"Invalid JSON from Reddit: {e} url={page.url}"
                ) from e

            listing = (payload.get("data") or {}) if isinstance(payload, dict) else {}
            children = listing.get("children") or []
            after = listing.get("after")

            logger.info(
                "JSON batch %d: children=%d after=%s",
                pages + 1,
                len(children),
                after,
            )

            if pages == 0 and len(children) == 0:
                # legitimate empty search vs soft block
                logger.warning("JSON first batch empty for keyword=%r", keyword)

            gained = 0
            stop = False

            for child in children:
                post = _json_child_to_post(child)
                if not post:
                    continue
                pid = post["post_id"]
                if pid in seen:
                    continue
                seen.add(pid)

                if last_post_id and pid == last_post_id:
                    logger.info("Stop JSON: checkpoint post_id=%s", pid)
                    stop = True
                    stop_reason = "checkpoint"
                    break

                created_raw = post.get("created_at")
                if created_raw:
                    try:
                        created = _parse_iso(created_raw)
                        if created < since_dt:
                            logger.info(
                                "Stop JSON: post_id=%s created=%s < since=%s",
                                pid,
                                created.isoformat(),
                                since_dt.isoformat(),
                            )
                            stop = True
                            stop_reason = "baseline"
                            break
                    except Exception as e:
                        logger.warning(
                            "Bad created_at post_id=%s value=%r err=%s",
                            pid,
                            created_raw,
                            e,
                        )
                        continue

                collected.append(post)
                gained += 1

            pages += 1

            if stop:
                break

            if gained == 0:
                no_progress += 1
                if no_progress >= settings.max_no_progress_attempts:
                    stop_reason = "no_progress"
                    break
            else:
                no_progress = 0

            if not after:
                stop_reason = "no_after"
                break

            await human_delay(settings.human_delay_min, settings.human_delay_max)

        return collected, stop_reason

    # ==================================================================
    # HTML fallback
    # ==================================================================
    async def _crawl_html(
        self,
        page: Page,
        *,
        keyword: str,
        since_dt: datetime,
        last_post_id: Optional[str],
        seen: Set[str],
        collected: List[Dict],
    ) -> List[Dict]:
        url = build_search_html_url(keyword)
        logger.info("HTML fallback keyword=%r url=%s", keyword, url)

        try:
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.navigation_timeout_ms,
            )
        except PlaywrightTimeout as e:
            raise NavigationError(f"HTML navigation timeout: {e}") from e

        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeout:
            pass

        status = response.status if response else 0
        logger.info(
            "HTML HTTP status=%s final_url=%s title=%r",
            status,
            page.url,
            await page.title(),
        )

        if status >= 400:
            raise NavigationError(f"HTML HTTP {status} for {url}")

        blocked = await _detect_block(page)
        if blocked:
            raise BlockDetectedError(
                f"Reddit block on HTML: {blocked} | url={page.url}"
            )

        await human_delay(settings.human_delay_min, settings.human_delay_max)

        pages = 0
        no_progress = 0
        stop = False

        while pages < settings.max_pages_per_task and not stop:
            batch = await self.parser.parse_listing(page)
            logger.info(
                "HTML batch %d: posts=%d url=%s",
                pages + 1,
                len(batch),
                page.url,
            )

            if pages == 0 and len(batch) == 0:
                blocked2 = await _detect_block(page)
                if blocked2:
                    raise BlockDetectedError(
                        f"Empty HTML listing + block: {blocked2} | url={page.url}"
                    )

            gained = 0
            for post in batch:
                pid = post.get("post_id")
                if not pid or pid in seen:
                    continue
                seen.add(pid)

                if last_post_id and pid == last_post_id:
                    logger.info("Stop HTML: checkpoint %s", pid)
                    stop = True
                    break

                created_raw = post.get("created_at")
                if created_raw:
                    try:
                        created = _parse_iso(created_raw)
                        if created < since_dt:
                            logger.info(
                                "Stop HTML: %s created=%s < since=%s",
                                pid,
                                created.isoformat(),
                                since_dt.isoformat(),
                            )
                            stop = True
                            break
                    except Exception:
                        continue

                collected.append(post)
                gained += 1

            if stop:
                break

            if gained == 0:
                no_progress += 1
                if no_progress >= settings.max_no_progress_attempts:
                    break
            else:
                no_progress = 0

            next_ok = await self._click_next_page(page)
            if not next_ok:
                if not await self._try_scroll(page):
                    break

            pages += 1
            blocked = await _detect_block(page)
            if blocked:
                raise BlockDetectedError(
                    f"Block mid HTML crawl: {blocked} | url={page.url}"
                )
            await human_delay(settings.human_delay_min, settings.human_delay_max)

        logger.info(
            "HTML crawl finished keyword=%r total=%d pages=%d",
            keyword,
            len(collected),
            pages,
        )
        return collected

    async def _click_next_page(self, page: Page) -> bool:
        try:
            next_btn = page.locator(sel.NEXT_BUTTON)
            if await next_btn.count() == 0:
                return False
            href = await next_btn.first.get_attribute("href")
            logger.info("Click next href=%s", href)
            await next_btn.first.click()
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=20000)
            except PlaywrightTimeout:
                pass
            return True
        except Exception as e:
            logger.warning("Next click failed: %s", e)
            return False

    async def _try_scroll(self, page: Page) -> bool:
        try:
            prev_h = await page.evaluate(
                "() => document.body ? document.body.scrollHeight : 0"
            )
            await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            await human_delay(settings.human_delay_min, settings.human_delay_max)
            cur_h = await page.evaluate(
                "() => document.body ? document.body.scrollHeight : 0"
            )
            return cur_h > prev_h
        except Exception:
            return False