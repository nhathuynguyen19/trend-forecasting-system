# Browser Resilience & Anti-Bot Guidelines

**Nhiệm vụ cốt lõi:** Khởi tạo, duy trì và cung cấp công cụ giả lập hành vi để bảo vệ Worker khỏi các hệ thống Anti-Bot (Datadome, Cloudflare) và tình trạng tràn RAM.

**Các quy tắc và điều kiện bắt buộc:**

1. **Khởi tạo Singleton & Tối ưu RAM:**
   - Trình duyệt Chromium tổng chỉ được phép bật lên một lần duy nhất khi toàn bộ quá trình Worker khởi động.
   - Bắt buộc phải gắn cờ `--disable-dev-shm-usage` và `--no-sandbox` vào cấu hình khởi tạo để ngăn chặn lỗi tràn bộ nhớ trên môi trường Docker.
2. **Cấp phát Tab tàng hình (Stealth Provisioning):**
   - Cung cấp hàm `get_stealth_page()` để tầng Core gọi mỗi khi có nhiệm vụ mới. Hàm này chịu trách nhiệm sinh ra một Tab mới từ trình duyệt tổng và phải tiêm các đoạn script ẩn danh (xóa dấu vết webdriver) vào Tab đó trước khi giao ra.
3. **Tiện ích độ trễ (Human Delay):**
   - Cung cấp hàm `human_delay(min_sec, max_sec)`. Hàm này phải sử dụng cơ chế sleep bất đồng bộ (async sleep) tạo ra các khoảng thời gian nghỉ ngẫu nhiên lẻ đến từng mili-giây, phục vụ cho các thao tác giả lập đọc tin, cuộn trang ở tầng Platform.