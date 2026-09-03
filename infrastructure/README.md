# Infrastructure — Social Trend Analyzer

Hạ tầng thời gian thực cho hệ thống phân tích xu hướng mạng xã hội. Sử dụng **Docker Compose** để khởi động local environment gồm Kafka (KRaft mode), Redis, ClickHouse.

## 🏗️ Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────┐
│              Docker Compose Local               │
│                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │  Kafka   │   │  Redis   │   │ ClickHouse   │ │
│  │  (KRaft) │   │  (Dedup) │   │   (Sink)     │ │
│  │  :9092   │   │ :6379    │   │   :8123      │ │
│  │  :29093  │   │          │   │              │ │
│  └──────────┘   └──────────┘   └──────────────┘ │
└─────────────────────────────────────────────────┘
```

### Các thành phần chính

| Thành phần | Image | Cổng | Mục đích |
|---|---|---|---|
| **Kafka** | `confluentinc/cp-kafka:7.5.0` | 9092 (client) / 29093 (controller) | Message broker — nhận & phục vụ dữ liệu thô |
| **Redis** | `redis:7-alpine` | 6379 | Deduplication — lọc post_id trùng lặp |
| **ClickHouse** | `clickhouse/clickhouse-server:latest` | 8123 (HTTP) | Columnar DB — lưu trữ trend để vẽ dashboard |
| **Kafka-UI** (nếu có) | `provectus/kafka-ui` | 8080 | Giao diện quản lý topic, consumer group |

## 🚀 Quick Start

### 1. Khởi động hạ tầng

```bash
make infra-up
```

Tương đương:
```bash
docker-compose -f infrastructure/docker-compose.yml up -d
```

### 2. Kiểm tra các service đang chạy

```bash
docker-compose -f infrastructure/docker-compose.yml ps
```

### 3. Tắt hạ tầng

```bash
make infra-down
```

hoặc (xóa sạch volume)

```bash
docker-compose -f infrastructure/docker-compose.yml down -v
```

### 4. Kiểm tra logs (ví dụ Kafka)

```bash
docker-compose -f infrastructure/docker-compose.yml logs kafka
```

## ⚙️ Cấu hình Kafka (KRaft mode)

### Giải thích các biến môi trường quan trọng

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `KAFKA_NODE_ID` | `1` | Mỗi broker có ID duy nhất (số nguyên ≥ 1) |
| `KAFKA_PROCESS_ROLES` | `broker,controller` | **KRaft combined mode** — broker + controller gộp cùng 1 node |
| `KAFKA_CONTROLLER_QUORUM_VOTERS` | `1@kafka:29093` | Danh sách controller voters (format: `nodeId@host:port`) |
| `KAFKA_LISTENERS` | `PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,PLAINTEXT_HOST://0.0.0.0:9092` | 3 listener: internal broker, controller, external client |
| `KAFKA_ADVERTISED_LISTENERS` | `PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092` | Địa chỉ mà client kết nối tới |
| `CLUSTER_ID` | `${KAFKA_CLUSTER_ID}` | ID cluster — tất cả node phải giống nhau |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | `1` | RF cho topic `__consumer_offsets` |

### Listener giải thích

| Listener | Port | Giao tiếp với | Mục đích |
|---|---|---|---|
| `PLAINTEXT` | 29092 | Các broker khác | Internal replication traffic |
| `CONTROLLER` | 29093 | Controller quorum | KRaft metadata management |
| `PLAINTEXT_HOST` | 9092 | Client bên ngoài | Producer/consumer kết nối từ host |

## 📦 Quản lý Topic

### Tạo topic

```bash
# Đăng nhập vào container Kafka
docker exec -it trend-pulse-kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --create \
  --topic social.posts.raw \
  --partitions 3 \
  --replication-factor 1
```

### Liệt kê tất cả topic

```bash
docker exec -it trend-pulse-kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

### Mô tả chi tiết topic

```bash
docker exec -it trend-pulse-kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --describe --topic social.posts.raw
```

### Xóa topic (cần `delete.topic.enable=true`)

```bash
docker exec -it trend-pulse-kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --delete --topic social.posts.raw
```

### Tăng số partition (không thể giảm)

```bash
docker exec -it trend-pulse-kafka kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --alter --topic social.posts.raw --partitions 6
```

## 🔍 Kiểm tra hệ thống

### Xem logs Kafka

```bash
docker logs -f trend-pulse-kafka
```

### Xem consumer groups hiện tại

```bash
docker exec -it trend-pulse-kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --list
```

### Mô tả 1 consumer group

```bash
docker exec -it trend-pulse-kafka kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group crawler-group
```

### Check lag (chênh lệch giữa producer & consumer)

```bash
docker exec -it trend-pulse-kafka kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic social.posts.raw --time -1
```

## 📊 Quy tắc chọn thông số cho phần cứng hạn chế

### Quy tắc chung

```
Replication Factor (RF) ≤ Số broker
Số Partition ≤ Số CPU cores × 2 (cho dev)
```

### Bảng cấu hình khuyến nghị

| Môi trường | Broker | RF | Partition | RAM khuyên | CPU khuyên |
|---|---|---|---|---|---|
| **Dev / Local** | 1 | 1 | 3–6 | 4 GB | 2 vCPU |
| **Demo / Pre-prod** | 3 | 3 | 6–12 | 8 GB × 3 | 2 vCPU × 3 |
| **Production** | 3+ | 3 | 12–24 | 16 GB × 3 | 4 vCPU × 3 |

### 🔑 Lời khuyên cho phần cứng hạn chế

- **Bắt đầu với 1 broker, RF=1** — không ảnh hưởng đến logic code
- **Topic `social.posts.raw`: 3 partitions** — đủ cho dev, đảm bảo consumer song song
- **Flink parallelism = 3** — matching số partition
- **Chỉ scale lên 3 broker** khi cần deploy thực tế cho group/project

## 🗂️ Cấu trúc thư mục

```
infrastructure/
├── docker-compose.yml      # Orchestration: Kafka, Redis, ClickHouse
├── .env.example            # Biến môi trường mẫu
├── README.md               # File này
└── .env                    # Biến môi trường thực (không commit)
```

## ⚠️ Lưu ý quan trọng

- **Không commit `.env`** — file chứa thông tin nhạy cảm (password, cluster ID)
- **Dữ liệu lưu trong volume** (`kafka-data`, `kafka-logs`) — xóa container không mất dữ liệu
- **Thay đổi partition** — chỉ tăng, không giảm được sau khi tạo topic
- **RF=1 không có failover** — dành cho dev, không dùng cho production
- **KRaft mode** — không cần ZooKeeper, đơn giản hơn nhưng cần lưu ý `controller.quorum.voters`

## 📚 Tài liệu tham khảo

- [Confluent Kafka KRaft docs](https://docs.confluent.io/platform/current/kafka/kraft.html)
- [Apache Kafka Official Docs](https://kafka.apache.org/documentation/)
- [Docker Compose Kafka examples](https://github.com/confluentinc/cp-docker-images)
