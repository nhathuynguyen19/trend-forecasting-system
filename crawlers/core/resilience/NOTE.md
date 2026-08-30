# 📝 Browser Resilience & Anti-Bot Guidelines (Tầng Quản lý Trình duyệt & Ẩn Danh)

**Mục tiêu:** Thư mục này đóng vai trò là "Lá chắn" bảo vệ hệ thống Crawler. Nó chịu trách nhiệm khởi tạo, duy trì và cấu hình trình duyệt Chromium ảo (Playwright) sao cho tối ưu RAM nhất và **giống người thật nhất**.

**Tuyệt đối KHÔNG viết code bóc tách HTML (DOM scraping) ở đây. Tầng này chỉ cung cấp Trình duyệt đã được ngụy trang cho các nền tảng sử dụng.**

## 🎯 4 Yêu cầu cốt lõi (Bắt buộc)

1. **Tàng hình (Stealth Mode Bắt Buộc):** 
   - Không bao giờ dùng Playwright "nguyên bản". Bắt buộc phải bơm thư viện `playwright-stealth` vào mỗi Tab (`Page`) mới mở để qua mặt Cloudflare / Datadome / reCAPTCHA.
2. **Tối ưu RAM (Singleton Context):** 
   - Trình duyệt (`Browser`) chỉ được `launch()` **1 lần duy nhất** khi Worker khởi động.
   - Các keyword khác nhau chỉ mở thêm các Tab mới (`new_page()`) dùng chung một Context. Tuyệt đối không mở Chromium mới cho mỗi từ khóa.
3. **Chống Crash (Docker Optimization):**
   - Phải thêm cờ `--disable-dev-shm-usage` và `--no-sandbox` vào arguments của Chromium để tránh lỗi tràn bộ nhớ (Out of Memory) khi chạy trên container Docker.
4. **Hành vi con người (Human-like Flow):**
   - Phải có các hàm `human_delay()` để mô phỏng thời gian nghỉ ngẫu nhiên giữa các thao tác lật trang hoặc click.

## 💻 Mã giả định hướng (Playwright Setup)

Bên dưới là bộ khung chuẩn (Boilerplate) cho file quản lý trình duyệt:

```python
# crawlers/core/resilience/browser_manager.py
import asyncio
import random
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

class StealthBrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None

    async def start_browser(self, proxy_url=None):
        """Được gọi 1 lần duy nhất ở main.py khi Worker khởi động"""
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled", # Tắt cờ tự động hoá
                "--no-sandbox",                                  # Bắt buộc trên Docker
                "--disable-dev-shm-usage",                       # Chống crash RAM
                "--disable-gpu"
            ]
        )
        
        # Tạo Context (giống như 1 profile người dùng với Cookie/Cache riêng)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            proxy={"server": proxy_url} if proxy_url else None
        )
        
        print("Stealth Browser started successfully.")

    async def get_stealth_page(self):
        """Được gọi bởi các platforms để xin một Tab mới làm việc"""
        page = await self.context.new_page()
        
        # Bơm script ẩn danh (xoá webdriver flag) VÀO TAB MỚI
        await stealth_async(page)
        return page

    async def close(self):
        """Đóng an toàn khi Worker bị tắt"""
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

# Utility functions cho các nền tảng sử dụng
async def human_delay(min_sec=1.5, max_sec=4.5):
    """Nghỉ ngẫu nhiên số lẻ để đánh lừa thuật toán phát hiện Bot"""
    delay = random.uniform(min
