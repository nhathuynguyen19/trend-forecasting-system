# Kafka Consumer Guidelines

**Nhiệm vụ cốt lõi:** Kết nối với Kafka để lắng nghe các lệnh thu thập từ topic `crawl-tasks.{platform}`. Chịu trách nhiệm quản lý vòng đời của một luồng công việc (nhận lệnh ➔ giao việc ➔ xác nhận hoàn thành). 

**Tuyệt đối KHÔNG chứa logic điều khiển Trình duyệt, không gọi Redis và không chứa logic bóc tách DOM tại tầng này.**

**Các quy tắc và điều kiện bắt buộc:**

1. **Bắt buộc sử dụng Consumer Group:**
   - Khi khởi tạo Consumer, phải luôn cấu hình một định danh nhóm cố định (ví dụ: `group_id="crawler-group"`). 
   - Điều này là bắt buộc để kích hoạt tính năng Auto-Scaling của Kafka, giúp hệ thống tự động chia đều các từ khóa (Partitions) cho các máy Worker khác nhau và tự động cân bằng lại tải (Rebalance) khi có máy bị chết hoặc cắm thêm máy mới.

2. **Xác nhận thủ công (Manual Offset Commit):**
   - Bắt buộc **TẮT** chế độ tự động xác nhận (`enable_auto_commit=False`).
   - Consumer chỉ được phép gửi lệnh xác nhận hoàn thành (commit offset) về cho Kafka **SAU KHI** toàn bộ quá trình cuộn trang, thu thập dữ liệu ở tầng Platform và đẩy kết quả lên topic thô (`social.posts.raw`) đã hoàn tất 100% không có lỗi.
   - Nếu xảy ra lỗi (crash, mất kết nối, lỗi DOM), tuyệt đối không commit. Kafka sẽ tự động giao lại lệnh này cho Worker khác (hoặc chính Worker này) xử lý lại vào lần sau.

3. **Quản lý Timeout (Max Poll Interval):**
   - Do đặc thù thu thập bằng Trình duyệt ảo yêu cầu các khoảng nghỉ ngẫu nhiên (`human_delay`) và cuộn trang liên tục, một tác vụ có thể kéo dài vài phút.
   - Bắt buộc phải cấu hình thông số `max_poll_interval_ms` của Kafka Consumer đủ dài (ví dụ: 10 - 15 phút) để tránh việc Kafka Broker hiểu lầm là Worker đã chết (timeout) và tước quyền xử lý từ khóa của Worker đó giữa chừng.

4. **Chuyển giao và Giải mã (Delegation & Decoding):**
   - Nhiệm vụ xử lý dữ liệu duy nhất ở đây là giải mã Message Value (từ dạng chuỗi JSON/Bytes) thành Object chứa `keyword` và `baseline_since`.
   - Lập tức truyền các tham số này sang cho hàm điều phối (Nhạc trưởng) của tầng Core xử lý. Khi hàm điều phối báo xong, Consumer tiến hành commit và quay lại trạng thái chờ lệnh mới.