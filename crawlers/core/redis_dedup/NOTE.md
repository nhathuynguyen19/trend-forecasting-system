# Redis Dedup & Checkpoint Guidelines (Tầng Quản Lý Trạng Thái & Lọc Trùng)

**Nhiệm vụ cốt lõi:** Giao tiếp với cơ sở dữ liệu Redis để lưu trữ, truy xuất tiến độ thu thập (Checkpoint) của từng từ khóa và đóng vai trò là tấm khiên loại bỏ các bài viết trùng lặp.

**Tuyệt đối KHÔNG chứa logic điều khiển Kafka, bóc tách DOM mạng xã hội hay thiết lập trình duyệt tại module này.**

**Các quy tắc và điều kiện bắt buộc:**

1. **Quy chuẩn Khóa lưu trữ (Key Convention):**
* Mọi thao tác lưu và đọc mốc kiểm tra (Checkpoint) bắt buộc phải tuân thủ định dạng khóa: `crawler:checkpoint:{platform}:{keyword}`.
* Giá trị (Value) của khóa này phải là chuỗi định danh gốc (`post_id`) của bài viết mới nhất được lấy về từ đợt chạy trước. Tuyệt đối không dùng thời gian (timestamp) làm giá trị Checkpoint để tránh sai số.


2. **Cập nhật trạng thái an toàn (State Update):**
* Chỉ được phép ghi đè (Set) `last_post_id` mới vào Redis **SAU KHI** toàn bộ quy trình thu thập và đẩy dữ liệu lên Kafka của một từ khóa đã hoàn tất thành công.
* Không được cập nhật Redis lắt nhắt từng bài một trong lúc đang cuộn trang để tránh làm hỏng điểm neo nếu tiến trình Worker đột ngột bị sập.


3. **Chống lặp tuyệt đối (Double-layer Shield):**
* Ngoài việc cung cấp mốc `last_post_id` cho tầng Platform làm điều kiện ngắt vòng lặp cuộn trang, module này cần cung cấp hàm kiểm tra nhanh sự tồn tại của một `post_id` bất kỳ.
* Khi mạng xã hội bị lỗi hiển thị lặp bài ở các trang khác nhau, hàm kiểm tra này sẽ gạt bỏ ngay lập tức những ID đã đi qua hệ thống, đảm bảo dữ liệu đưa sang Kafka Producer sạch 100%.


4. **Tối ưu Kết nối (Connection Pool):**
* Phải khởi tạo một Connection Pool (hồ chứa kết nối) duy nhất (Singleton) tới Redis khi Worker khởi động.
* Tuyệt đối không được mở và đóng kết nối Redis liên tục cho mỗi lần quét bài viết, tránh làm cạn kiệt tài nguyên mạng (Port exhaustion).
* Phải bắt lỗi kết nối (Timeout/Connection Refused). Nếu Redis sập, bắt buộc phải ném lỗi (Throw Exception) lên tầng Core để báo ngừng toàn bộ phiên làm việc, không được phép chạy tiếp khi mất hệ thống kiểm soát trạng thái.
