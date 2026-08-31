# Platforms Adapters Guidelines

**Nhiệm vụ cốt lõi:** Tiếp nhận Tab ẩn danh, trực tiếp giả lập hành vi con người để cuộn trang, đọc cấu trúc HTML (DOM) và quyết định thời điểm dừng lại.

**Các quy tắc và điều kiện bắt buộc:**

1. **Vòng lặp cuộn trang & Hành vi người thật:**
   - Duy trì một vòng lặp cuộn trang (Infinite Scroll). 
   - Sau mỗi lệnh cuộn xuống cuối màn hình, bắt buộc phải gọi hàm `human_delay()` từ module `resilience` để tạm nghỉ với thời gian ngẫu nhiên, mô phỏng người dùng đang chờ load thêm bài.
2. **Chốt chặn kép (Double-Stop Condition):** 
   - Trong quá trình quét các bài viết đang hiển thị trên màn hình, phải kiểm tra liên tục từng bài và ngắt vòng lặp cuộn trang ngay lập tức nếu thỏa mãn 1 trong 2 điều kiện:
     * Điều kiện chính: Bóc ra được ID bài viết trùng khớp hoàn toàn với `last_post_id` do Core truyền xuống.
     * Điều kiện phụ: (Dành cho lần chạy đầu khi `last_post_id` trống) Thời gian đăng bài cũ hơn mốc `baseline_since`.
3. **Bảo vệ dữ liệu cục bộ (Dedup In-memory):**
   - Do mạng xã hội load dữ liệu động, các bài viết có thể bị trồi sụt trên màn hình. Phải duy trì một danh sách lưu trữ các ID đã quét trong cùng một lần chạy để bỏ qua các bài bị lặp lại trên DOM.
4. **Cô lập logic:**
   - Output trả về cho Core chỉ là một mảng/danh sách các đối tượng bài viết đã được làm sạch. Không được phép nhúng logic Kafka hay Redis vào tầng này.