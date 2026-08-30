# Hướng Dẫn Phát Triển - Bộ Máy Đếm Tin Siêu Tốc (flink-processor)

Thư mục này chứa mã nguồn xử lý dòng dữ liệu lớn thời gian thực bằng Apache Flink.

---

## 1. Nhiệm Vụ Cốt Lõi

Nhận luồng dữ liệu bài viết thô từ Hộp thư Kafka (topic `social.posts.raw`), gom nhóm các bài viết theo từ khóa (`keyBy('keyword')`), đếm số lượng bài viết xuất hiện trong các cửa sổ thời gian 5 phút cố định (Tumbling Window) và ghi nhận kết quả xuống ClickHouse và Redis.

---

## 2. Quy Tắc Lập Trình Bắt Buộc

1. **Tuân thủ quy chuẩn dữ liệu POJO**:
   * Class [EventRecord](src/main/java/com/trend/model/EventRecord.java) bắt buộc phải có constructor không tham số và đầy đủ getter/setter để Flink tuần tự hóa (serialize) dữ liệu tốc độ cao. Không được đổi cấu trúc lớp này mà không đồng bộ với bên Ingestion (Crawler).
2. **Xử lý lỗi Parse JSON**:
   * Khi chuyển đổi chuỗi JSON thô từ Kafka sang `EventRecord`, phải dùng khối `try/catch` bọc hàm đọc của Jackson `ObjectMapper`. Nếu tin nhắn bị lỗi cú pháp, trả về `null` và dùng bộ lọc `.filter(record -> record != null)` để loại bỏ tin lỗi, tuyệt đối không được để lỗi làm dừng toàn bộ luồng đếm của Flink.
3. **Cấu hình song song (Parallelism)**:
   * Mức độ song song của nguồn đọc (Source Parallelism) phải được cấu hình khớp 1:1 với số lượng phân vùng (Partitions) của Kafka topic `social.posts.raw` (mặc định là 24) để tối ưu băng thông đọc.
4. **Đóng gói Shadow/Fat JAR**:
   * Khi thêm bất kỳ thư viện Java nào mới, phải khai báo trong [build.gradle](build.gradle). Nếu thư viện đó đã có sẵn trên cụm máy chủ Flink (như flink-streaming, flink-clients), hãy dùng `compileOnly`. Nếu là thư viện ngoài (như Kafka connector, Redis client), dùng `implementation` để Shadow Plugin tự động đóng gói vào file JAR cuối cùng mang đi chạy.
