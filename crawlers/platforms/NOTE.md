# 📝 Platforms Adapters Guidelines (Tầng Thu thập & Bóc tách DOM)

**Mục tiêu:** Nhận một Tab trình duyệt ảo (`page`) đã được ngụy trang an toàn từ tầng Core. Mở link từ khóa, giả lập thao tác cuộn trang (infinite scroll), bóc tách dữ liệu HTML và **dừng cuộn ngay lập tức** khi phát hiện ID bài viết trùng với mốc Checkpoint.

**Tuyệt đối KHÔNG cấu hình hay khởi tạo trình duyệt Playwright ở đây. Chỉ sử dụng đối tượng `page` được truyền vào.**

## 🎯 3 Yêu cầu cốt lõi (Bắt buộc)

1. **Cuộn trang an toàn:** Không được cuộn liên tục không ngừng. Phải sử dụng hàm `human_delay` (từ `core.resilience`) để nghỉ ngẫu nhiên sau mỗi lần cuộn trang, chờ DOM render bài mới.
2. **Selector ổn định:** Ưu tiên dùng các thuộc tính HTML cấu trúc (`data-id`, `datetime`, `id`) thay vì class CSS dễ bị thay đổi.
3. **Double-Stop (Chốt chặn kép):** 
   - Vòng lặp bóc tách phải dừng ngay (break) khi `post_id` bóc được bằng với `last_post_id` (đã crawl đợt trước).
   - Nếu `last_post_id` rỗng (lần chạy đầu tiên), phải dừng khi bài viết cũ hơn `baseline_since`.

## 💻 Mã giả định hướng (Playwright DOM Scraping)

```python
# crawlers/platforms/reddit/adapter.py
from core.resilience.browser_manager import human_delay
from shared_contracts.schemas import StandardPost

async def fetch_new_posts(keyword, page, last_post_id, baseline_since):
    """
    page: Tab trình duyệt ẩn danh được cấp từ Core
    last_post_id: ID bài viết mới nhất của đợt crawl trước (Lấy từ Redis)
    """
    await page.goto(f"[https://www.reddit.com/search?q=](https://www.reddit.com/search?q=){keyword}&sort=new")
    await human_delay(2, 4) # Đợi trang load xong

    extracted_posts = []
    seen_ids_in_this_run = set() # Chống lặp bài trong cùng 1 lần cuộn trang
    keep_scrolling = True
    
    while keep_scrolling:
        # 1. Tìm tất cả các thẻ bài viết đang hiển thị trên màn hình
        post_elements = await page.locator("shreddit-post").all()
        
        for element in post_elements:
            post_id = await element.get_attribute("id")
            
            if not post_id or post_id in seen_ids_in_this_run:
                continue
                
            seen_ids_in_this_run.add(post_id)

            # ĐIỂM DỪNG CHÍNH: Bắt gặp ID cũ -> Ngắt vòng lặp cuộn trang
            if post_id == last_post_id:
                keep_scrolling = False
                break
                
            # Trích xuất nội dung
            text_content = await element.locator(".feed-post-text").inner_text()
            created_at = await element.locator("time").get_attribute("datetime")
            
            # ĐIỂM DỪNG PHỤ: Cho lần chạy đầu (Chưa có last_post_id)
            if not last_post_id and created_at < baseline_since:
                keep_scrolling = False
                break
                
            # Đóng gói theo chuẩn Shared Contract
            post = StandardPost(
                platform="reddit",
                post_id=post_id,
                text=text_content.strip(),
                created_at=created_at
            )
            extracted_posts.append(post)

        if keep_scrolling:
            # 2. Cuộn chuột xuống cuối trang để ép load thêm bài mới
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            
            # 3. Nghỉ ngẫu nhiên giống người thật để chờ data đổ về
            await human_delay(1.5, 3.5)
            
            # TODO: Dev cần thêm logic đếm số lần cuộn không có bài mới để break (phòng hờ hết data)
            
    return extracted_posts
