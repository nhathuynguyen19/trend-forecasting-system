# Hướng Dẫn - Bảng Đo Chỉ Số Sức Khỏe (observability)

Thư mục này quản lý cấu hình hệ thống giám sát thời gian thực phục vụ lấy số liệu thực nghiệm cho bài báo khoa học / luận văn.

---

## 1. Nhiệm Vụ Cốt Lõi

Thu thập, lưu trữ và hiển thị các biểu đồ về thông số hoạt động của Flink và Kafka (độ trễ xử lý, lượng tin nhắn nghẽn - Lag, phần trăm CPU/RAM tiêu thụ) thông qua Prometheus và Grafana.

---

## 2. Mô tả các Thư mục Con (Sẽ tạo sau)

* **`prometheus/`** (Bộ thu thập chỉ số):
  * Chứa file cấu hình `prometheus.yml` định nghĩa các địa chỉ (Endpoints) mà Prometheus cần kết nối tới để lấy chỉ số (như Flink JMX Metric Exporter, Kafka Exporter).
* **`grafana/`** (Bộ vẽ biểu đồ trực quan):
  * Chứa cấu hình nguồn dữ liệu (Data Sources) kết nối tới Prometheus.
* **`dashboards/`** (Mẫu biểu đồ sẵn có):
  * Lưu các tệp JSON xuất bản dashboard trực quan. Chứa 2 dashboard chính:
    1. **Flink Performance Dashboard**: Theo dõi độ trễ (latency), băng thông (throughput) và số lượng tin nhắn xử lý thành công trên từng giây.
    2. **Kafka Cluster Dashboard**: Theo dõi chỉ số nghẽn (Lag) trên từng partition và tình trạng hoạt động của các Broker.

---

## 3. Các Chỉ Số Bắt Buộc Phải Đo Được

Để có đủ dữ liệu thuyết phục trong báo cáo khoa học, hệ thống giám sát phải xuất ra được 4 thông số sau:
1. **Kafka Consumer Lag**: Số lượng tin nhắn bị ùn ứ chưa kịp xử lý trong topic `social.posts.raw`.
2. **Flink Processing Latency**: Thời gian trung bình để Flink xử lý xong 1 tin nhắn kể từ khi nó đi vào hệ thống.
3. **Flink Throughput**: Số lượng tin nhắn mà Flink xử lý được trong 1 giây.
4. **Resource Utilization**: Phần trăm CPU và dung lượng bộ nhớ RAM mà Flink JobManager và TaskManager đang tiêu thụ.
