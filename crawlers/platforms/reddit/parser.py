"""DOM extraction for Reddit listings."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from platforms.reddit import selectors as sel

logger = logging.getLogger("crawler.reddit.parser")

_ID_RE = re.compile(
    r"^[a-z0-9]{5,12}$",
    re.I,
)


def parse_score(
    text: Optional[str],
    title_attr: Optional[str] = None,
) -> Optional[int]:

    if title_attr:

        value = title_attr.strip()

        if value.lstrip("-").isdigit():

            try:
                return int(value)

            except ValueError:
                pass

    if not text:
        return None

    text = text.strip().replace(",", "")

    if text in ("•", "–", "-", ""):
        return None

    match = re.search(
        r"([-+]?[\d.]+)\s*([kKmM]?)",
        text,
    )

    if not match:
        return None

    try:
        value = float(match.group(1))

    except ValueError:
        return None

    unit = (match.group(2) or "").lower()

    if unit == "k":
        value *= 1000

    elif unit == "m":
        value *= 1_000_000

    return int(value)


def parse_num_comments(
    text: Optional[str],
) -> int:

    if not text:
        return 0

    text = text.strip().lower()

    if text in ("comment", "comments"):
        return 0

    match = re.search(
        r"([\d,]+)",
        text,
    )

    if not match:
        return 0

    try:
        return int(
            match.group(1).replace(",", "")
        )

    except ValueError:
        return 0


def parse_created_at(
    ts_raw: Optional[str],
) -> Optional[str]:

    if not ts_raw:
        return None

    value = str(ts_raw).strip()

    if not value.isdigit():
        return None

    try:
        timestamp = int(value)

    except ValueError:
        return None

    if (
        timestamp < 1_100_000_000
        or timestamp > 4_000_000_000
    ):
        return None

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).isoformat()


def validate_raw(
    post: Dict[str, Any],
) -> tuple[bool, str]:

    pid = (
        post.get("post_id")
        or ""
    ).strip()

    if not pid:
        return False, "invalid post_id"

    if not _ID_RE.match(pid):
        return False, f"invalid post_id: {pid!r}"

    if not (
        post.get("title")
        or ""
    ).strip():

        return False, "empty title"

    permalink = (
        post.get("permalink")
        or ""
    ).strip()

    if (
        not permalink
        or "/comments/" not in permalink
    ):

        return False, (
            f"invalid permalink: "
            f"{permalink[:80]!r}"
        )

    return True, "ok"


class RedditParser:

    @classmethod
    async def parse_listing(
        cls,
        page: Page,
    ) -> List[Dict[str, Any]]:

        posts: List[Dict[str, Any]] = []

        # ==========================================================
        # WAIT FOR OLD REDDIT LISTING
        # ==========================================================

        try:

            await page.wait_for_selector(
                sel.LISTING,
                timeout=15000,
            )

        except PlaywrightTimeout:

            logger.info(
                "Timeout waiting for Reddit listing "
                "url=%s",
                page.url,
            )

            return []

        # ==========================================================
        # FIND POSTS
        # ==========================================================

        things = page.locator(
            sel.PRIMARY_THING
        )

        count = await things.count()

        used = sel.PRIMARY_THING

        if count == 0:

            things = page.locator(
                sel.FALLBACK_THING
            )

            count = await things.count()

            used = sel.FALLBACK_THING

        logger.info(
            "Found %d things selector=%r",
            count,
            used,
        )

        # ==========================================================
        # PARSE EACH POST
        # ==========================================================

        for i in range(count):

            try:

                raw = await cls._parse_one(
                    things.nth(i)
                )

                if raw is None:
                    continue

                ok, reason = validate_raw(raw)

                if not ok:

                    logger.info(
                        "Skip post: %s",
                        reason,
                    )

                    continue

                posts.append(raw)

            except Exception as e:

                logger.info(
                    "Parse error #%d: %s",
                    i,
                    e,
                )

        return posts

    @classmethod
    async def _parse_one(
        cls,
        thing,
    ) -> Optional[Dict[str, Any]]:

        # ==========================================================
        # POST ID
        # ==========================================================

        fullname = (
            await thing.get_attribute(
                "data-fullname"
            )
            or ""
        )

        post_id = (
            fullname[3:]
            if fullname.startswith("t3_")
            else fullname
        )

        if not post_id:

            element_id = (
                await thing.get_attribute(
                    "id"
                )
                or ""
            )

            match = re.search(
                r"t3_([a-z0-9]+)",
                element_id,
                re.I,
            )

            if match:
                post_id = match.group(1)

        if not post_id:
            return None

        # ==========================================================
        # PROMOTED
        # ==========================================================

        promoted = await thing.get_attribute(
            "data-promoted"
        )

        if (
            promoted
            and promoted.lower() == "true"
        ):
            return None

        # ==========================================================
        # TITLE
        # ==========================================================

        title = ""

        title_el = thing.locator(
            sel.TITLE
        )

        if await title_el.count() > 0:

            title = (
                await title_el.first.inner_text()
            ).strip()

        if not title:
            return None

        # ==========================================================
        # AUTHOR
        # ==========================================================

        author = (
            await thing.get_attribute(
                "data-author"
            )
            or ""
        )

        if not author:

            author_el = thing.locator(
                sel.AUTHOR
            )

            if await author_el.count() > 0:

                author = (
                    await author_el.first.inner_text()
                ).strip()

        if not author:
            author = "[deleted]"

        # ==========================================================
        # CONTENT
        # ==========================================================

        content = ""

        body = thing.locator(
            sel.BODY
        )

        if await body.count() > 0:

            content = (
                await body.first.inner_text()
            ).strip()

        # ==========================================================
        # SCORE
        # ==========================================================

        score_attr = await thing.get_attribute(
            "data-score"
        )

        score_text = None

        score_el = thing.locator(
            sel.SCORE
        )

        if await score_el.count() > 0:

            score_text = (
                await score_el.first.inner_text()
            ).strip()

            title_attr = (
                await score_el.first.get_attribute(
                    "title"
                )
            )

            if title_attr:
                score_attr = (
                    score_attr
                    or title_attr
                )

        score = (
            parse_score(
                score_text,
                score_attr,
            )
            or 0
        )

        # ==========================================================
        # COMMENTS
        # ==========================================================

        comments_attr = (
            await thing.get_attribute(
                "data-comments-count"
            )
        )

        num_comments = 0

        if (
            comments_attr
            and str(comments_attr).isdigit()
        ):

            num_comments = int(
                comments_attr
            )

        else:

            comments_el = thing.locator(
                sel.COMMENTS
            )

            if await comments_el.count() > 0:

                num_comments = (
                    parse_num_comments(
                        (
                            await comments_el.first.inner_text()
                        ).strip()
                    )
                )

        # ==========================================================
        # URL
        # ==========================================================

        data_permalink = (
            await thing.get_attribute(
                "data-permalink"
            )
            or ""
        )

        data_url = (
            await thing.get_attribute(
                "data-url"
            )
            or ""
        )

        permalink = ""
        url = ""

        if data_permalink:

            permalink = (
                data_permalink
                if data_permalink.startswith(
                    "http"
                )
                else urljoin(
                    "https://www.reddit.com",
                    data_permalink,
                )
            )

        if data_url:

            url = (
                data_url
                if data_url.startswith("http")
                else urljoin(
                    "https://www.reddit.com",
                    data_url,
                )
            )

        # ==========================================================
        # FALLBACK PERMALINK
        # ==========================================================

        if not permalink:

            comments_el = thing.locator(
                sel.COMMENTS
            )

            if await comments_el.count() > 0:

                href = (
                    await comments_el.first.get_attribute(
                        "href"
                    )
                    or ""
                ).strip()

                if href:

                    permalink = (
                        href
                        if href.startswith("http")
                        else urljoin(
                            "https://www.reddit.com",
                            href,
                        )
                    )

        if not url:
            url = permalink

        # ==========================================================
        # CREATED AT
        # ==========================================================

        created_at = parse_created_at(
            await thing.get_attribute(
                "data-timestamp"
            )
        )

        return {
            "post_id": post_id,
            "title": title,
            "content": content,
            "author": author,
            "score": score,
            "num_comments": num_comments,
            "url": url or "",
            "permalink": permalink or "",
            "created_at": created_at,
        }