# Social Trend Analyzer

Hệ thống phân tích xu hướng mạng xã hội thời gian thực phục vụ nghiên cứu thực nghiệm tối ưu hóa hiệu năng và tự động co giãn tài nguyên.

*(Dự án tập trung hoàn toàn vào kỹ thuật phần mềm phân tán, xử lý luồng hiệu năng cao và tự động hóa điều phối tài nguyên, không áp dụng các mô hình học máy AI/ML để đảm bảo tiến độ và độ tin cậy thực nghiệm).*

## Cấu trúc thư mục dự án

Dưới đây là sơ đồ cây thư mục của dự án kèm mô tả chi tiết nhiệm vụ của từng thư mục:

```
social-trend-analyzer/
├── application-control/          # UI và API điều khiển tạo các tác vụ thu thập dữ liệu (Crawl Tasks)
├── crawlers/                     # Nhóm Crawler Workers (Reddit, Threads...) thu thập dữ liệu thô đưa vào Kafka
├── flink-processor/              # Công cụ xử lý luồng dữ liệu thời gian thực (real-time stream processing) bằng Flink
├── kafka-infrastructure/         # Định nghĩa cấu hình cluster Kafka, topic và các setup script
├── adaptive-controller/           # [LÕI NGHIÊN CỨU] Giám sát tải hệ thống, đo lường QoS và tối ưu tự động cấu hình Flink
├── observability/                 # Cấu hình Prometheus, Grafana thu thập metrics phục vụ thực nghiệm nghiên cứu
├── experiments/                   # Các kịch bản chạy thực nghiệm đối chứng (baseline vs adaptive) để viết báo cáo khoa học
├── shared-contracts/              # Định nghĩa schema truyền thông điệp dùng chung (Avro, Protobuf, JSON)
└── infrastructure/                # Các file triển khai Docker Compose local (Kafka, Redis, ClickHouse) và Kubernetes k8s
```

## Bắt đầu nhanh (Quick Start)

### 1. Khởi chạy hạ tầng thời gian thực (Local Environment)
Tại thư mục gốc, chạy lệnh để khởi động Kafka, Redis, Qdrant và ClickHouse:
```bash
make infra-up
```

### 2. Biên dịch Flink Processor
Vào thư mục `flink-processor` và build shadow jar:
```bash
cd flink-processor
.\gradlew shadowJar
```
Thành phẩm sẽ nằm trong thư mục `flink-processor/build/libs/`.
