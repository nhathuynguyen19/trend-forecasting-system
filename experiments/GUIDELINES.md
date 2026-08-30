# Hướng Dẫn - Phòng Thí Nghiệm (experiments)

Thư mục này quản lý toàn bộ các kịch bản chạy thử nghiệm, sinh tải giả lập và xuất báo cáo kết quả thực nghiệm tự động để viết luận văn.

---

## 1. Nhiệm Vụ Cốt Lõi

Tự động hóa hoàn toàn việc cấu hình hệ thống, sinh tải dữ liệu đầu vào theo các kịch bản định sẵn (tĩnh và động), đo đạc hiệu năng và ghi kết quả vào tệp tin CSV để vẽ đồ thị khoa học đối chứng.

---

## 2. Mô tả các Thư mục Con (Sẽ tạo sau)

* **`workloads/`** (Bộ sinh tải giả lập):
  * Chứa script Python sinh tin nhắn giả lập đẩy trực tiếp vào Kafka với tốc độ cấu hình được (ví dụ: `--rate 1000` tin nhắn/giây). Giúp bạn chủ động kiểm soát khối lượng tải đầu vào mà không cần chạy Crawler thật.
* **`baseline-default/`** (Cấu hình chạy thô):
  * Chứa cấu hình mặc định (ví dụ: Flink chạy với Parallelism = 2 cố định, không tối ưu, không tự co giãn). Làm mốc đối chứng cơ bản.
* **`static-optimized/`** (Cấu hình tối ưu tĩnh):
  * Chứa cấu hình tối ưu sẵn cho từng ngưỡng tải (ví dụ: Tải thấp dùng 2 partitions, tải cao dùng 12 partitions).
* **`adaptive/`** (Cấu hình thích ứng động):
  * Cấu hình bật bộ điều khiển `adaptive-controller` tự động tăng giảm máy ảo Flink theo thời gian thực.
* **`evaluation/`** (Bộ điều phối & vẽ biểu đồ):
  * `orchestrator.py`: Script tự động chạy vòng lặp đổi cấu hình -> chạy thử nghiệm -> lấy số liệu từ ClickHouse/Prometheus -> ghi vào file `results.csv`.
  * `plotter.py`: Script đọc file `results.csv` tự động vẽ các đồ thị khoa học (Latency vs. Throughput, Resource vs. Lag) để chèn vào báo cáo.

---

## 3. Quy Tắc Chạy Thực Nghiệm

1. **Thời gian chạy tối thiểu (Stability window)**:
   * Mỗi kịch bản thử nghiệm tĩnh hoặc động phải được chạy liên tục trong **tối thiểu 5 - 10 phút** để hệ thống Flink đi vào trạng thái ổn định (steady-state) trước khi thu thập số liệu.
2. **Dọn dẹp tài nguyên giữa các lần test**:
   * Trước khi chuyển sang một cấu hình test mới, bộ điều phối phải ra lệnh tắt toàn bộ các container Docker Compose, xóa sạch dữ liệu lưu tạm trong Kafka/Redis để đảm bảo lần test sau không bị ảnh hưởng bởi dữ liệu thừa của lần test trước.
3. **Độ tin cậy dữ liệu**:
   * Mỗi bài test nên được chạy lặp lại 3 lần để lấy giá trị trung bình, giảm thiểu sai số do hệ điều hành hoặc đường truyền mạng nội bộ gây ra.
