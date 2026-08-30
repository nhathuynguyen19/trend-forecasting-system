# Crawler Core Guidelines

**Nhiệm vụ cốt lõi:** Là trung tâm điều khiển của Worker. Quản lý trạng thái, phân bổ tài nguyên và đẩy dữ liệu cuối cùng, nhưng **tuyệt đối không** tự thực hiện các hành vi cuộn trang hay bóc tách HTML.

**Các quy tắc và luồng giao tiếp bắt buộc:**

1. **Tra cứu điểm neo (Checkpoint Lookup):**
   - Ngay khi nhận được lệnh (gồm `keyword` và `baseline_since`) từ Kafka, phải truy vấn vào Redis bằng khóa `crawler:checkpoint:{platform}:{keyword}`.
   - Kết quả trả về (nếu có) chính là `last_post_id` – ID của bài viết mới nhất đã lấy ở đợt trước.
2. **Cấp phát tài nguyên Trình duyệt:**
   - Gọi sang module `resilience` (hàm `get_stealth_page()`) để xin một Tab trình duyệt ẩn danh (Stealth Tab).
3. **Ủy quyền thu thập (Delegation to Platforms):**
   - Gọi hàm xử lý của tầng `platforms` và truyền vào đầy đủ 4 tham số: Đối tượng Tab trình duyệt, `keyword`, `last_post_id`, và `baseline_since`.
4. **Đóng gói và Lưu trạng thái:**
   - Đợi tầng `platforms` trả về danh sách các bài viết sạch. Đẩy toàn bộ vào topic `social.posts.raw`.
   - Lấy ID của bài viết mới nhất (đứng đầu danh sách) lưu đè vào Redis làm chốt chặn cho lần chạy tiếp theo.
   - Bắt buộc ra lệnh đóng Tab trình duyệt ngay khi xong việc để giải phóng RAM.
