# Kafka Producer Guidelines

**Nhiệm vụ cốt lõi:** Nhận dữ liệu đã chuẩn hóa từ tầng Service và đẩy lệnh an toàn vào Kafka để giao việc cho cụm Crawler Worker. Không chứa bất kỳ logic nghiệp vụ nào khác.

**Các quy tắc và điều kiện bắt buộc:**

1. **Định tuyến động (Dynamic Routing):**
   - Lệnh phải được bắn vào đúng topic tương ứng với nền tảng theo định dạng `crawl-tasks.{platform}`. Tuyệt đối không hardcode tên topic.
2. **Khóa dữ liệu (Message Key) - Điều kiện sống còn:**
   - Kafka Message bắt buộc phải có thuộc tính `Key`, và giá trị của `Key` chính là `keyword` cần thu thập.
   - Do topic được cấu hình dạng Compacted, việc gắn Key đảm bảo lệnh mới sẽ ghi đè lệnh cũ của cùng một từ khóa, đồng thời ép Kafka luôn giao một từ khóa cố định cho cùng một máy Worker.
3. **Đóng gói Payload:**
   - Dữ liệu (Value) của Message phải được định dạng thành JSON String, chứa chính xác hai trường: `keyword` và `baseline_since`.
4. **Cơ chế an toàn (Resilience):**
   - Phải thiết lập tự động thử lại (Retry) ít nhất 3 lần khi không kết nối được Kafka.
   - Nếu thất bại hoàn toàn, phải ném lỗi (Throw Exception) ngược lại cho tầng Service xử lý, tuyệt đối không được "nuốt lỗi" để lệnh rơi vào khoảng không.
