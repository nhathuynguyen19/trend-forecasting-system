import asyncio
import json
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright, TimeoutError

VN_TZ = timezone(timedelta(hours=7))

def setup_config():
    config_data = {
        "keyword": "AI",
        "since": "2026-08-31T12:00:00+07:00"
    }
    with open("temp.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)

def parse_reddit_time(ts_str):
    """Chuẩn hóa chuỗi thời gian của Reddit để Python 3.10 có thể đọc được."""
    if not ts_str:
        return None
    # Đổi 'Z' hoặc '+0000' thành chuẩn '+00:00'
    normalized = ts_str.replace("Z", "+00:00").replace("+0000", "+00:00")
    return datetime.fromisoformat(normalized)

async def main():
    setup_config()

    with open("temp.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    keyword = data["keyword"]
    since_dt = datetime.fromisoformat(data["since"])

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        url = f"https://www.reddit.com/search/?q={keyword}&type=link&sort=new"
        print(f"Đang mở URL: {url}")

        await page.goto(url, wait_until="domcontentloaded")

        post_selector = 'shreddit-post, [data-testid="search-sdui-post"]'

        try:
            await page.wait_for_selector(post_selector, timeout=15000)
        except TimeoutError:
            print("Không tìm thấy bài viết (Timeout). Có thể do mạng chậm hoặc bị Reddit chặn.")
            html = await page.content()
            with open("error_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Đã xuất file 'error_dump.html' để kiểm tra lỗi.")
            await browser.close()
            return

        scroll_attempts = 0
        while True:
            posts = await page.locator(post_selector).all()
            if not posts:
                break

            last_post = posts[-1]

            timeago = last_post.locator("faceplate-timeago").first
            created_ts = None
            if await timeago.count() > 0:
                created_ts = await timeago.get_attribute("ts")
            else:
                created_ts = await last_post.get_attribute("created-timestamp")

            if created_ts:
                post_dt = parse_reddit_time(created_ts)
                print(f"Đã cuộn tới bài: {post_dt.astimezone(VN_TZ).isoformat()}")

                if post_dt < since_dt:
                    print("=> Đã chạm mốc thời gian since. Dừng cuộn!")
                    break

            count_before = len(posts)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            try:
                # Dùng native locator để chờ bài viết mới (bài ở vị trí count_before) xuất hiện
                # Cách này vượt qua hoàn toàn rào cản CSP unsafe-eval của Reddit
                await page.locator(post_selector).nth(count_before).wait_for(state="attached", timeout=5000)
            except TimeoutError:
                print("=> Không có bài viết mới nào được tải thêm. Dừng cuộn!")
                break

            scroll_attempts += 1
            if scroll_attempts > 30:
                print("=> Đạt giới hạn an toàn 30 lần cuộn. Dừng!")
                break

        # ==== BÓC TÁCH DỮ LIỆU SẠCH ====
        extracted_data = []
        final_posts = await page.locator(post_selector).all()

        for post in final_posts:
            timeago = post.locator("faceplate-timeago").first
            created_ts = await timeago.get_attribute("ts") if await timeago.count() > 0 else await post.get_attribute("created-timestamp")

            if not created_ts:
                continue

            post_dt = parse_reddit_time(created_ts)
            if post_dt < since_dt:
                continue

            ctx_str = await post.get_attribute("data-faceplate-tracking-context")
            title, author, post_id = "", "", ""

            if ctx_str:
                try:
                    ctx = json.loads(ctx_str)
                    title = ctx.get("post", {}).get("title", "")
                    post_id = ctx.get("post", {}).get("id", "").replace("t3_", "")
                    author = ctx.get("profile", {}).get("name", "")
                except:
                    pass

            if not title: title = await post.get_attribute("post-title") or ""
            if not author: author = await post.get_attribute("author") or ""
            if not post_id: post_id = (await post.get_attribute("data-thingid") or "").replace("t3_", "")

            url = ""
            title_link = post.locator('a[data-testid="post-title-text"]').first
            if await title_link.count() > 0:
                href = await title_link.get_attribute("href")
                url = f"https://www.reddit.com{href}" if href and href.startswith("/") else href

            extracted_data.append({
                "post_id": post_id,
                "title": title.strip(),
                "author": author.strip(),
                "created_at": created_ts,
                "url": url,
            })

        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)

        print(f"HOÀN TẤT: Đã trích xuất {len(extracted_data)} bài viết hợp lệ ra tệp 'result.json'.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
