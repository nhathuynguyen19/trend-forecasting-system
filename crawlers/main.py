import asyncio
import json
import random
import os
import logging
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright, TimeoutError

# === CẤU HÌNH LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("reddit_crawler")

VN_TZ = timezone(timedelta(hours=7))

# === THÔNG SỐ BẢO VỆ (Dành cho .env và README) ===
HUMAN_DELAY_MIN = 2.0      # Nghỉ tối thiểu giữa các thao tác (giây)
HUMAN_DELAY_MAX = 5.0      # Nghỉ tối đa giữa các thao tác (giây)
MAX_RETRIES = 3            # Số lần thử lại tối đa nếu bị lỗi/chặn
INITIAL_BACKOFF = 5.0      # Giây chờ trước khi thử lại lần 1 (Exponential Backoff)
LOOP_INTERVAL_MIN = 30.0   # Chờ tối thiểu giữa các chu kỳ quét (giây)
LOOP_INTERVAL_MAX = 60.0   # Chờ tối đa giữa các chu kỳ quét (giây)
MAX_SCROLLS = 30           # Giới hạn số lần cuộn trang để tránh vòng lặp vô tận

def setup_config():
    if not os.path.exists("temp.json"):
        config_data = {
            "keyword": "AI",
            "since": "2026-08-31T22:00:00+07:00"
        }
        with open("temp.json", "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        logger.info("Đã tạo file cấu hình mẫu temp.json")

def parse_reddit_time(ts_str):
    if not ts_str:
        return None
    normalized = ts_str.replace("Z", "+00:00").replace("+0000", "+00:00")
    return datetime.fromisoformat(normalized)

async def main():
    setup_config()
    seen_post_ids = set()

    async with async_playwright() as p:
        logger.info("Khởi động Playwright Chromium...")
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        while True:
            with open("temp.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            keyword = data["keyword"]
            since_dt = datetime.fromisoformat(data["since"])

            logger.info(f"=== BẮT ĐẦU CHU KỲ QUÉT (Từ mốc: {since_dt.astimezone(VN_TZ).isoformat()}) ===")

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()

            url = f"https://www.reddit.com/search/?q={keyword}&type=link&sort=new"

            retry_count = 0
            success = False
            extracted_data = []

            while retry_count < MAX_RETRIES and not success:
                try:
                    delay_start = random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX)
                    logger.info(f"Đang chờ ngẫu nhiên {delay_start:.1f}s trước khi mở trang...")
                    await asyncio.sleep(delay_start)

                    logger.info(f"Đang điều hướng URL: {url}")
                    await page.goto(url, wait_until="domcontentloaded", timeout=45000)

                    post_selector = 'shreddit-post, [data-testid="search-sdui-post"]'
                    await page.wait_for_selector(post_selector, timeout=15000)

                    scroll_attempts = 0
                    while scroll_attempts < MAX_SCROLLS:
                        posts = await page.locator(post_selector).all()
                        if not posts:
                            break

                        last_post = posts[-1]
                        timeago = last_post.locator("faceplate-timeago").first
                        created_ts = await timeago.get_attribute("ts") if await timeago.count() > 0 else await last_post.get_attribute("created-timestamp")

                        if created_ts:
                            post_dt = parse_reddit_time(created_ts)
                            if post_dt <= since_dt:
                                logger.info(f"Đã chạm mốc thời gian ({post_dt.astimezone(VN_TZ).isoformat()}). Dừng cuộn.")
                                break

                        count_before = len(posts)
                        logger.info(f"Đang cuộn trang để tải thêm (Lần {scroll_attempts + 1})...")
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await asyncio.sleep(random.uniform(HUMAN_DELAY_MIN, HUMAN_DELAY_MAX))

                        try:
                            await page.locator(post_selector).nth(count_before).wait_for(state="attached", timeout=5000)
                        except TimeoutError:
                            logger.warning("Không có bài viết mới (Có thể đã đến đáy trang kết quả).")
                            break

                        scroll_attempts += 1

                    logger.info("Tiến hành bóc tách dữ liệu...")
                    final_posts = await page.locator(post_selector).all()
                    for post in final_posts:
                        timeago = post.locator("faceplate-timeago").first
                        created_ts = await timeago.get_attribute("ts") if await timeago.count() > 0 else await post.get_attribute("created-timestamp")

                        if not created_ts: continue
                        post_dt = parse_reddit_time(created_ts)

                        if post_dt <= since_dt:
                            continue

                        ctx_str = await post.get_attribute("data-faceplate-tracking-context")
                        title, author, post_id = "", "", ""

                        if ctx_str:
                            try:
                                ctx = json.loads(ctx_str)
                                title = ctx.get("post", {}).get("title", "")
                                post_id = ctx.get("post", {}).get("id", "").replace("t3_", "")
                                author = ctx.get("profile", {}).get("name", "")
                            except: pass

                        if not title: title = await post.get_attribute("post-title") or ""
                        if not author: author = await post.get_attribute("author") or ""
                        if not post_id: post_id = (await post.get_attribute("data-thingid") or "").replace("t3_", "")

                        if post_id in seen_post_ids:
                            continue
                        seen_post_ids.add(post_id)

                        url_str = ""
                        title_link = post.locator('a[data-testid="post-title-text"]').first
                        if await title_link.count() > 0:
                            href = await title_link.get_attribute("href")
                            url_str = f"https://www.reddit.com{href}" if href and href.startswith("/") else href

                        extracted_data.append({
                            "post_id": post_id,
                            "title": title.strip(),
                            "author": author.strip(),
                            "created_at": created_ts,
                            "url": url_str,
                        })

                    success = True
                except Exception as e:
                    retry_count += 1
                    backoff_time = INITIAL_BACKOFF * (2 ** (retry_count - 1))
                    logger.error(f"Lỗi: {e}.")
                    logger.warning(f"Chờ {backoff_time}s và thử lại ({retry_count}/{MAX_RETRIES})...")
                    await asyncio.sleep(backoff_time)

            await context.close()

            if success:
                if extracted_data:
                    if os.path.exists("result.json"):
                        with open("result.json", "r", encoding="utf-8") as f:
                            try:
                                existing_data = json.load(f)
                            except:
                                existing_data = []
                    else:
                        existing_data = []

                    existing_data.extend(extracted_data)
                    with open("result.json", "w", encoding="utf-8") as f:
                        json.dump(existing_data, f, indent=2, ensure_ascii=False)

                    newest_post = max(extracted_data, key=lambda x: parse_reddit_time(x["created_at"]))
                    data["since"] = parse_reddit_time(newest_post["created_at"]).isoformat()

                    with open("temp.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    logger.info(f"Thành công! Đã thu thập {len(extracted_data)} bài mới. Cập nhật since = {data['since']}")
                else:
                    logger.info("Thành công! Không có bài viết mới nào xuất hiện.")
            else:
                logger.error("Chu kỳ bị hủy do lỗi mạng hoặc chặn IP vượt quá số lần Retry.")

            wait_time = random.uniform(LOOP_INTERVAL_MIN, LOOP_INTERVAL_MAX)
            logger.info(f"Nghỉ {wait_time:.1f} giây trước chu kỳ tiếp theo...\n")
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    asyncio.run(main())
