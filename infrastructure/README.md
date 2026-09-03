# Infrastructure — Social Trend Analyzer

Hạ tầng thời gian thực cho hệ thống phân tích xu hướng mạng xã hội, phục vụ nghiên cứu thực nghiệm tối ưu hóa hiệu năng và tự động co giãn tài nguyên.

> **Lưu ý:** Dự án tập trung vào kỹ thuật phần mềm phân tán, xử lý luồng hiệu năng cao và tự động hóa điều phối tài nguyên — không sử dụng mô hình học máy AI/ML để đảm bảo tiến độ và độ tin cậy thực nghiệm.

## 🏗️ Tổng quan kiến trúc

Hạ tầng local được khởi động bằng **Docker Compose** với 4 dịch vụ chính:

```
┌──────────────────────────────────────────────────────────┐
│                  Docker Compose Local                    │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐       │
│  │  Kafka   │    │  Redis   │    │ ClickHouse   │       │
│  │  (KRaft) │    │  (Dedup) │    │   (Sink)     │       │
│  │  :9092   │    │ :6379    │    │   :8123      │       │
│  │  :29093  │    │          │    │   :9000      │       │
│  └────┬─────┘    └────┬─────┘    └──────────────┘       │
│       │              │                                  │
│       │         Crawler Workers                         │
│       │         (Playwright + Kafka Producer)           │
│       │                                                  │
│  ┌────▼──────────────────────────────────────────┐      │
│  │              Qdrant (Vector Search)            │      │
│  │              :6333 / :6334                     │      │
│  └──────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────┘
```

## 📦 Các dịch vụ

| Dịch vụ | Image | Cổng | Vai trò |
|---|---|---|---|
| **Kafka** | `confluentinc/cp-kafka:7.5.0` | `9092` (client) / `29093` (controller) | Message broker — nhận & phục vụ dữ liệu thô |
| **Redis** | `redis:7.0-alpine` | `6379` | Deduplication — lọc post_id trùng lặp |
| **ClickHouse** | `clickhouse/clickhouse-server:latest` | `8123` (HTTP) / `9000` (Native) | Columnar DB — lưu trữ trend phục vụ dashboard |
| **Qdrant** | `qdrant/qdrant:latest` | `6333` / `6334` | Vector database — tìm kiếm ngữ nghĩa (nếu có) |

## 🚀 Quick Start

### 1. Khởi động hạ tầng

```bash
make infra-up
```

Tương đương:
```bash
docker-compose -f infrastructure/docker-compose.yml up -d
```

### 2. Kiểm tra trạng thái dịch vụ

```bash
docker-compose -f infrastructure/docker-compose.yml ps
```

### 3. Xem logs

```bash
docker-compose -f infrastructure/docker-compose.yml logs -f kafka
docker-compose -f infrastructure/docker-compose.yml logs -f redis
docker-compose -f infrastructure/docker-compose.yml logs -f clickhouse
docker-compose -f infrastructure/docker-compose.yml logs -f qdrant
```

### 4. Tắt hạ tầng

```bash
make infra-down
```

## ⚙️ Cấu hình Kafka (KRaft mode)

### Giải thích các biến môi trường

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `KAFKA_NODE_ID` | `1` | Mỗi broker có ID duy nhất (số nguyên ≥ 1) |
| `KAFKA_PROCESS_ROLES` | `broker,controller` | **KRaft combined mode** — broker + controller gộp cùng 1 node |
| `KAFKA_CONTROLLER_QUORUM_VOTERS` | `1@kafka:29093` | Danh sách controller voters (format: `nodeId@host:port`) |
| `KAFKA_LISTENERS` | `PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,PLAINTEXT_HOST://0.0.0.0:9092` | 3 listener: internal broker, controller, external client |
| `KAFKA_ADVERTISED_LISTENERS` | `PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092` | Địa chỉ mà client kết nối tới |
| `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP` | `CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT` | Map listener name → protocol |
| `KAFKA_INTER_BROKER_LISTENER_NAME` | `PLAINTEXT` | Listener dùng cho replication giữa các broker |
| `KAFKA_CONTROLLER_LISTENER_NAMES` | `CONTROLLER` | Listener dùng cho KRaft controller quorum |
| `CLUSTER_ID` | `${KAFKA_CLUSTER_ID}` | ID cluster — tất cả node phải giống nhau |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | `1` | RF cho topic `__consumer_offsets` |
| `KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR` | `1` | RF cho transaction state log |

### Listener giải thích

| Listener | Port | Giao tiếp với | Mục đích |
|---|---|---|---|
| `PLAINTEXT` | 29092 | Các broker/controller khác | Internal replication traffic |
| `CONTROLLER` | 29093 | Controller quorum | KRaft metadata management |
| `PLAINTEXT_HOST` | 9092 | Client bên ngoài | Producer/consumer kết nối từ host |

### Environment variables (`.env.example`)

```bash
# Infrastructure Ports
KAFKA_PORT=9092
REDIS_PORT=6379
QDRANT_PORT=6333

# Redis Configuration
REDIS_PASSWORD=redis_pwd

# Kafka Configuration
KAFKA_CLUSTER_ID=4L62StMTRvOt6sn9Zglstag
```

## 📦 Quản lý Topic

### Đăng nhập vào container Kafka

```bash
docker exec -it trend-pulse-kafka /bin/bash
```

### Tạo topic

```bash
# Đơn giản (auto-create enabled)
# Hoặc tạo thủ công:
kafka-topics.sh --bootstrap-server localhost:9092 \
  --create --topic social.posts.raw --partitions 3 --replication-factor 1
```

### Liệt kê tất cả topic

```bash
kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Mô tả chi tiết topic

```bash
kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic social.posts.raw
```

### Xóa topic (cần `delete.topic.enable=true`)

```bash
kafka-topics.sh --bootstrap-server localhost:9092 --delete --topic social.posts.raw
```

### Tăng số partition (chỉ tăng, không giảm được)

```bash
kafka-topics.sh --bootstrap-server localhost:9092 \
  --alter --topic social.posts.raw --partitions 6
```

## 🔍 Kiểm tra hệ thống

### Xem consumer groups

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list
```

### Mô tả consumer group (kiểm tra lag)

```bash
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group crawler-group
```

### Check offset (vị trí tiêu thụ)

```bash
kafka-run-class.sh kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic social.posts.raw --time -1
```

### Test Redis kết nối

```bash
docker exec -it trend-pulse-redis redis-cli -a redis_pwd ping
```

### Test ClickHouse kết nối

```bash
docker exec -it trend-pulse-clickhouse clickhouse-client --query "SELECT 1"
```

## 📊 Quy tắc chọn thông số cho phần cứng hạn chế

### Quy tắc cơ bản

```
Replication Factor (RF) ≤ Số broker
Số Partition ≤ Số CPU cores × 2 (cho dev)
Số consumer trong group ≤ Số partition
```

### Bảng cấu hình khuyến nghị

| Môi trường | Broker | RF | Partition | RAM khuyên | CPU khuyên |
|---|---|---|---|---|---|
| **Dev / Local** | **1** | 1 | 3–6 | 4 GB | 2 vCPU |
| **Demo / Pre-prod** | 3 | 3 | 6–12 | 8 GB × 3 | 2 vCPU × 3 |
| **Production** | 3+ | 3 | 12–24 | 16 GB × 3 | 4 vCPU × 3 |

### 🔑 Lời khuyên cho phần cứng hạn chế

- **Bắt đầu với 1 broker, RF=1** — không ảnh hưởng đến logic code
- **Topic `social.posts.raw`: 3 partitions** — đủ cho dev
- **Flink parallelism = 3** — matching số partition
- **Chỉ scale lên 3 broker** khi cần deploy thực tế cho group/project

### 📈 Khi muốn scale lên

- Thêm broker → tăng RF tương ứng (RF=3 cần ≥ 3 broker)
- Thêm partition → tăng parallelism cho Flink consumer
- Đảm bảo `min.insync.replicas` ≤ RF

## 🔗 Kết nối giữa các dịch vụ

```
Crawler Worker → Kafka (:29092 DOCKER listener)
  → social.posts.raw topic (24 partitions, RF=3 trong thiết kế)
    → Flink Source (parallelism = số partition)
      → keyBy('keyword') → Window (5 phút) → Aggregation
        → ClickHouse / Redis (Sink)

Redis ← Crawler Worker (dedup post_id)
  → Đảm bảo không crawl trùng bài

Qdrant ← (nếu có vector embedding)
  → Tìm kiếm ngữ nghĩa
```

## 🗂️ Cấu trúc thư mục

```
infrastructure/
├── docker-compose.yml      # Orchestration: Kafka, Redis, ClickHouse, Qdrant
├── .env.example            # Biến môi trường mẫu
├── README.md               # File này
└── .env                    # Biến môi trường thực (không commit)
```

## ⚠️ Lưu ý quan trọng

- **Không commit `.env`** — file chứa thông tin nhạy cảm (password, cluster ID)
- **Dữ liệu lưu trong volume** (`kafka-data`, `redis-data`, `clickhouse-data`, `qdrant-data`) — xóa container không mất dữ liệu
- **Thay đổi partition** — chỉ tăng, không giảm được sau khi tạo topic
- **RF=1 không có failover** — dành cho dev, không dùng cho production
- **KRaft mode** — không cần ZooKeeper, đơn giản hơn nhưng cần lưu ý `controller.quorum.voters`
- **Healthcheck** — Redis và Kafka đều có healthcheck, `depends_on` dùng điều kiện healthy nên crawler khởi động sau khi hạ tầng sẵn sàng

## 📚 Tài liệu tham khảo

- [Confluent Kafka KRaft docs](https://docs.confluent.io/platform/current/kafka/kraft.html)
- [Apache Kafka Official Docs](https://kafka.apache.org/documentation/)
- [Docker Compose Kafka examples](https://github.com/confluentinc/cp-docker-images)
- [ClickHouse Docker docs](https://clickhouse.com/docs/en/operations/docker-compose)
- [Qdrant Docker docs](https://github.com/qdrant/qdrant/tree/master/docs/quick-start/docker-compose.md)
