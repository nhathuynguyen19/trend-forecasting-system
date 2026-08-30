# Kafka Producer Guidelines (Tầng Xuất Dữ Liệu Thô)

**Nhiệm vụ cốt lõi:** Tiếp nhận danh sách các bài viết đã được bóc tách và làm sạch từ các nền tảng, sau đó đẩy toàn bộ lên topic dữ liệu thô trung tâm của hệ thống (`social.posts.raw`) để chờ Flink xử lý.

**Tuyệt đối KHÔNG chứa logic gọi API, không điều khiển trình duyệt và không tự ý thêm bớt các trường dữ liệu nằm ngoài quy chuẩn ở tầng này.**

**Các quy tắc và điều kiện bắt buộc:**

1. **Đích đến tập trung (Single Topic Target):**
   - Khác với Consumer phải nghe nhiều topic (`crawl-tasks.reddit`, `crawl-tasks.facebook`), Producer ở đây chỉ được phép bắn dữ liệu vào một đích đến duy nhất: topic `social.posts.raw`.
   - Mọi dữ liệu từ mọi nền tảng đều phải hội tụ về đây.

2. **Chống mất dữ liệu (Zero Data Loss):**
   - Khi khởi tạo Producer, bắt buộc phải cấu hình `acks=all` (hoặc `acks=-1`). 
   - Điều này ép Kafka phải xác nhận toàn bộ các bản sao (Replicas) trên cụm Cluster đều đã lưu dữ liệu thành công thì mới báo kết quả về cho hàm gọi. 
   - Nếu xảy ra lỗi đẩy dữ liệu (Timeout, Disconnect), phải ném lỗi (Throw Exception) ngược về tầng Core. Tầng Core sẽ báo lỗi cho Consumer để ngưng việc commit lệnh, đảm bảo tính toàn vẹn của tiến trình.

3. **Chiến lược Phân mảnh (Partition Key Strategy):**
   - Mọi tin nhắn (Message) gửi đi bắt buộc phải được gắn `Key` là giá trị của `keyword` (Ví dụ: "Artificial Intelligence").
   - Mục đích: Đảm bảo toàn bộ bài viết thuộc cùng một từ khóa sẽ luôn được Kafka điều hướng vào cùng một Partition. Việc này sẽ tối ưu hóa hiệu năng cực kỳ lớn cho hệ thống xử lý thời gian thực (Apache Flink) ở luồng sau khi tiến hành gom nhóm (`keyBy('keyword')`).

4. **Tuân thủ Hợp đồng Dữ liệu (Schema Compliance):**
   - Trước khi gửi đi, dữ liệu phải được ép kiểu và định dạng thành JSON String (hoặc Avro/Protobuf nếu có cấu hình).
   - Cấu trúc dữ liệu gửi lên bắt buộc phải khớp 100% với định dạng chuẩn đã được thống nhất tại thư mục `shared-contracts`. Tuyệt đối không được rò rỉ các trường dữ liệu rác, cấu trúc dị biệt của DOM (HTML class, thuộc tính lạ) lên topic này để tránh làm sập bộ giải mã của Flink.
