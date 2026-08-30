# 📝 Crawler Core Guidelines (Tầng Thu thập bằng Trình duyệt Ảo)

**Mục tiêu:** Điều khiển Chromium (Playwright) để mở trang, **cuộn trang (scroll)** liên tục để tải dữ liệu, và dừng cuộn ngay lập tức khi quét thấy DOM chứa bài viết cũ (trùng ID trong Redis).

## 🎯 Yêu cầu cốt lõi (Bắt buộc)
1. **Async Context:** Playwright hoạt động tốt nhất ở môi trường Asynchronous. Code ở tầng core phải sử dụng `async/await` để không block luồng.
2. **Infinite Scroll (Cuộn vô tận):** Thay vì dùng `next_cursor`, trình duyệt ảo phải giả lập hành vi cuộn chuột xuống cuối trang, chờ (wait) cho DOM render thêm bài viết mới, sau đó tiếp tục quét.
3. **Cơ chế Checkpoint:** Vẫn giữ nguyên logic lưu Post ID vào Redis. Dừng cuộn trang khi element HTML chứa `data-id` trùng với `last_post_id`.

## 💻 Mã giả định hướng (Playwright Async Logic)

```python
# crawlers/core/fetcher.py
import asyncio

async def fetch_new_posts_via_browser(platform, keyword, baseline_since):
    redis_key = f"crawler:checkpoint:{platform}:{keyword}"
    last_post_id = redis_client.get(redis_key)
    
    # Lấy instance của trình duyệt từ module resilience
    page = await browser_manager.get_page(platform)
    await page.goto(f"https://www.{platform}.com/search?q={keyword}")
    
    newest_post_id_this_run = None
    keep_scrolling = True
    
    while keep_scrolling:
        # 1. Trích xuất tất cả bài viết đang hiện trên màn hình
        posts = await extract_posts_from_dom(page) # Hàm này do thư mục platforms/ định nghĩa
        
        for post in posts:
            if newest_post_id_this_run is None:
                newest_post_id_this_run = post['id']
                
            # ĐIỂM DỪNG: Bắt gặp ID cũ -> Dừng cuộn trang
            if post['id'] == last_post_id:
                keep_scrolling = False
                break 
                
            produce_to_raw_topic(post)
            
        if keep_scrolling:
            # 2. Giả lập cuộn chuột để tải thêm bài viết (Lazy load)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # Chờ một chút để mạng xã hội load HTML mới
            await asyncio.sleep(2) 
            
            # TODO: Thêm logic break nếu cuộn quá nhiều mà không có bài mới (hết data)
            
    # 3. Cập nhật Redis Checkpoint
    if newest_post_id_this_run:
        redis_client.set(redis_key, newest_post_id_this_run)
