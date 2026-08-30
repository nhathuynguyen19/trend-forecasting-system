# Đề Cương Nghiên Cứu Khoa Học - Social Trend Analyzer

Tài liệu này lưu trữ định hướng nghiên cứu khoa học, câu hỏi nghiên cứu, phương pháp thực nghiệm và lộ trình 3 tháng của dự án **Social Trend Analyzer**.

---

## 1. Mục Tiêu Nghiên Cứu Cốt Lõi

Nghiên cứu hành vi hiệu năng và khả năng tự động điều phối tài nguyên của hệ thống xử lý luồng dữ liệu lớn thời gian thực (Apache Flink & Kafka) dưới các áp lực tải (Workloads) biến động đột ngột từ mạng xã hội.

> **Lưu ý quan trọng**: Đề tài không áp dụng các mô hình học máy AI/ML phức tạp (Sentence-BERT, DBSCAN) để đảm bảo độ tin cậy thực nghiệm cao nhất và hoàn thành đúng thời hạn ngắn (3 tháng). Xu hướng được phát hiện dựa trên các đột biến về số lượng bài viết (Volume-Spike) theo cửa sổ thời gian.

---

## 2. Các Câu Hỏi Nghiên Cứu (Research Questions - RQ)

* **RQ1 (Tối ưu cấu hình tĩnh - Static Tuning)**:
  * *Câu hỏi*: Mối quan hệ giữa cấu hình phần cứng tĩnh (Số lượng Partition trong Kafka, mức độ song song - Parallelism trong Flink) và các chỉ số hiệu năng (Độ trễ xử lý - Latency, Băng thông - Throughput) của luồng dữ liệu lớn là gì? Làm sao xác định được cấu hình tối ưu chi phí cho các ngưỡng tải (Workload) tĩnh khác nhau?
* **RQ2 (Cơ chế co giãn thích ứng - Adaptive Scaling)**:
  * *Câu hỏi*: Cơ chế tự động co giãn (Auto-scaling) dựa trên hệ luật ngưỡng đơn giản (giám sát Kafka Lag và CPU) giúp cải thiện độ trễ và tiết kiệm bao nhiêu phần trăm tài nguyên so với cấu hình tĩnh trong kịch bản tải biến động liên tục?
* **RQ3 (Đo lường hao phí co giãn - Rescaling Overhead)**:
  * *Câu hỏi*: Việc dừng luồng để phân chia lại trạng thái (Savepoint & Restore) khi Flink thực hiện co giãn động gây ra hao phí (Overhead) bao nhiêu giây về độ trễ đỉnh (Spike Latency)? Ngưỡng trễ này có chấp nhận được trong phân tích xu hướng thời gian thực không?

---

## 3. Các Đóng Góp Khoa Học Của Đề Tài

1. **Performance Dataset (Bộ dữ liệu thực nghiệm)**:
   * Cung cấp một ma trận số liệu thực tế về hành vi của Flink 1.19 và Kafka dưới nhiều mức độ tải và cấu hình phần cứng khác nhau, đóng vai trò làm tài liệu tham khảo cho các nghiên cứu tối ưu hóa tài nguyên sau này.
2. **Automated Performance Benchmarking Tool (Bộ đo tự động)**:
   * Đóng góp một kiến trúc tự động hóa hoàn toàn từ khâu giả lập tải đầu vào (Workload Generator), đo đạc lưu trữ dữ liệu hiệu năng (ClickHouse/Prometheus) đến tự động vẽ biểu đồ trực quan hóa.
3. **Threshold-based Scaling Rulebook (Bộ quy tắc điều phối động)**:
   * Thiết kế một giải pháp điều phối thích ứng động dạng ngưỡng (Rule-based Thresholds) tối giản nhưng đạt hiệu năng gần tương đương với các thuật toán học máy phức tạp (như Reinforcement Learning) nhưng có chi phí tính toán cực kỳ thấp và dễ triển khai thực tế.

---

## 4. Kịch Bản Thực Nghiệm (Methodology)

Thực nghiệm được thực hiện thông qua 2 track nghiên cứu đối chứng tại thư mục `experiments/`:

### Track 1: Thực nghiệm Tĩnh (Static Grid Search)
* Chạy hệ thống dưới 4 ngưỡng tải cố định: **Thấp** (100 tin/s), **Trung bình** (1.000 tin/s), **Cao** (5.000 tin/s), và **Cực đại** (20.000 tin/s).
* Thay đổi lần lượt các tham số (Số lượng Partition, Parallelism) để đo đạc và vẽ đồ thị tìm ra bộ tham số tĩnh tối ưu nhất cho từng ngưỡng tải.

### Track 2: Thực nghiệm Thích Ứng Động (Adaptive Evaluation)
* Chạy hệ thống dưới kịch bản tải mô phỏng biến động hình sin hoặc đột biến (để giả lập sự kiện nóng ngoài đời thực).
* Bật bộ điều khiển `adaptive-controller` để tự động tăng/giảm TaskManager của Flink dựa trên Kafka Lag.
* So sánh các chỉ số hiệu năng và lượng CPU tiêu thụ với Track 1 để đưa ra kết luận.
