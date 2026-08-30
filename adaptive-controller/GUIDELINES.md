# Hướng Dẫn Phát Triển - Người Giám Sát Thông Minh (adaptive-controller)

Thư mục này chứa lõi nghiên cứu tự động điều phối tài nguyên và cấu hình hệ thống thời gian thực dựa trên tải đầu vào.

---

## 1. Nhiệm Vụ Cốt Lõi

Tự động hóa việc theo dõi trạng thái sức khỏe của hệ thống (lượng thư ùn ứ - Lag trong Kafka, phần trăm CPU của máy đếm Flink) và ra quyết định tăng/giảm quy mô (Scale out/in) số lượng máy ảo TaskManager hoặc cấu hình lại hệ thống Flink để tối ưu chi phí và đảm bảo độ trễ thấp.

---

## 2. Mô tả các Thư mục Con (Sẽ tạo sau)

* **`monitoring/`** (Bộ phận theo dõi):
  * Chứa code định kỳ (ví dụ 10 giây/lần) gọi API sang Prometheus để lấy các thông số: tốc độ dòng dữ liệu đầu vào (Workload), số lượng tin nhắn đang bị nghẽn trong Kafka (Lag), và độ tiêu thụ CPU của các Flink TaskManager.
* **`workload/`** (Phân tích tải):
  * Nhận dữ liệu từ bộ phận theo dõi để phân loại xem tải hiện tại đang ở mức nào: Thấp, Trung bình, Cao, hay Cực đại.
* **`qos/`** (Giám sát chất lượng):
  * Tính toán xem hệ thống có đang đảm bảo đúng cam kết chất lượng dịch vụ (QoS) hay không (ví dụ: độ trễ xử lý tin nhắn có vượt quá 1 giây hay không).
* **`optimizer/`** (Bộ não quyết định):
  * Chứa thuật toán luật ngưỡng (Rule-based Thresholds). Ví dụ:
    * *Luật 1*: Nếu Lag > 5000 tin nhắn liên tục trong 30 giây $\rightarrow$ Ra lệnh Scale Up (Thêm máy).
    * *Luật 2*: Nếu CPU < 20% liên tục trong 5 phút $\rightarrow$ Ra lệnh Scale Down (Bớt máy để tiết kiệm tiền).
* **`reconfiguration/`** (Bộ thực thi):
  * Nhận lệnh từ bộ não để thực hiện hành động: gọi Kubernetes API để tăng/giảm replicas của Flink TaskManager, hoặc gọi Flink REST API để nộp cấu hình mới.

---

## 3. Quy Tắc Hoạt Động Bắt Buộc

1. **Tránh dao động liên tục (Rescaling Flapping)**:
   * Quá trình co giãn của Flink mất từ 5-15 giây để dừng và khôi phục từ điểm lưu trạng thái (Savepoint). Do đó, bộ điều phối phải có cơ chế lọc nhiễu, chỉ ra lệnh scale khi tải thay đổi thực sự ổn định trong một khoảng thời gian (ví dụ: chỉ scale up sau 30 giây nghẽn, chỉ scale down sau 5 phút rảnh rỗi).
2. **Cơ chế Ngắt Tự Động (Bypass Switch)**:
   * Phải có một cấu hình bật/tắt (on/off) cho bộ điều phối này. Khi chạy các bài test tĩnh (Track 1) để lấy số liệu đối chứng, bộ điều phối này bắt buộc phải được tắt để không can thiệp vào hệ thống.
3. **Log chi tiết hành động**:
   * Mỗi khi ra quyết định scale, bắt buộc phải log lại thời gian, trạng thái trước khi scale, cấu hình sau khi scale và thời gian hoàn tất quá trình scale (Downtime) để làm số liệu viết luận văn.
