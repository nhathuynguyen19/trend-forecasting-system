# Kiến Trúc Hệ Thống - Social Trend Analyzer

Tài liệu này đặc tả chi tiết kiến trúc và luồng dữ liệu của hệ thống **Social Trend Analyzer** dựa trên thiết kế 3 Subgraph cốt lõi.

---

## 1. Tổng Quan Kiến Trúc (3 Subgraphs)

Hệ thống được chia thành 3 phân vùng xử lý độc lập, kết nối với nhau qua hệ thống hàng đợi Kafka:

```
┌────────────────────────────────────────────────────────┐
│             SUBGRAPH 1: Data Ingestion                 │
│  [Control Panel] ──(crawl-tasks)──► [Crawler Workers]  │
└───────────────────────────┬────────────────────────────┘
                            │ (social.posts.raw)
                            ▼
┌────────────────────────────────────────────────────────┐
│           SUBGRAPH 2: Kafka Infrastructure             │
│  [Kafka Cluster] (3 Brokers, 24 Partitions per topic)  │
└───────────────────────────┬────────────────────────────┘
                            │ (Parallel Stream, p=24)
                            ▼
┌────────────────────────────────────────────────────────┐
│            SUBGRAPH 3: Real-time Processing            │
│  [Flink Processor] ──► [ClickHouse] / [Redis] ──► [UI] │
└────────────────────────────────────────────────────────┘
```

---

## 2. Đặc Tả Chi Tiết Từng Subgraph

### Subgraph 1: Data Ingestion (Thu thập dữ liệu)
* **Bảng điều khiển (Control Panel)**: 
  * Gửi lệnh thu thập tin tức định dạng JSON: `{"platform": "reddit", "keyword": "AI", "since": "2026-08-23T00:00:00Z"}`.
  * Lệnh được gửi vào topic dạng Compacted có tên `crawl-tasks.{platform}` (ví dụ: `crawl-tasks.reddit` với 3 partitions).
* **Robot thu thập (Crawler Workers)**:
  * Được thiết kế dưới dạng một nhóm co giãn động (Dynamic Auto-Scaling Pool) gồm từ 1 đến tối đa 3 máy (Workers).
  * Kafka sẽ tự động cân bằng tải (Rebalance) phân chia các phân vùng (Partitions/Keywords) cho các Worker đang sống.
  * Mỗi Worker khi nhận được tác vụ sẽ:
    1. Kiểm tra điểm neo (Checkpoint ID) trong **Redis Dedup** bằng key `crawler:checkpoint:{platform}:{keyword}` để lấy ID của bài viết mới nhất đã cào đợt trước (`last_post_id`).
    2. Gọi API hoặc giả lập trình duyệt ẩn danh (Stealth Tab) để cào dữ liệu từ mạng xã hội từ thời điểm `since` hoặc sau `last_post_id`.
    3. Lọc trùng lặp bài viết bằng cách đối chiếu ID bài viết với **Redis Dedup** (chống lưu trùng lặp dữ liệu thô).
    4. Đẩy danh sách bài viết sạch vào topic `social.posts.raw` của Kafka.
    5. Lưu ID bài viết mới nhất đè lại vào Redis để làm điểm neo cho lần cào kế tiếp.

### Subgraph 2: Kafka Infrastructure (Hạ tầng hàng đợi)
* **Topic dữ liệu thô (`social.posts.raw`)**:
  * Được cấu hình lớn với **24 Partitions** và hệ số nhân bản **Replication Factor = 3** để đảm bảo khả năng chịu lỗi và băng thông cao.
  * Phân phối đều trên 3 Kafka Broker:
    * Broker 1: Quản lý và làm Leader cho Partitions 0-7.
    * Broker 2: Quản lý và làm Leader cho Partitions 8-15.
    * Broker 3: Quản lý và làm Leader cho Partitions 16-23.
* **Cơ chế ghi/đọc**:
  * Các Crawler Worker đẩy dữ liệu vào Kafka sử dụng cơ chế gom lô (batching) và cam kết an toàn (`acks=all`).
  * Flink Processor sẽ kết nối và đọc song song trực tiếp từ 24 partitions này (Parallelism = 24), đảm bảo tỷ lệ 1-1 không bị nghẽn cổ chai.

### Subgraph 3: Real-time Processing (Xử lý luồng Flink)
* **Flink Source Tasks**: Nhận luồng dữ liệu song song từ 24 partitions của topic `social.posts.raw`.
* **Network Shuffle (xáo trộn mạng)**: Thực hiện gom nhóm dữ liệu theo từ khóa bằng hàm `keyBy('keyword')`. Tất cả các bài viết có cùng từ khóa sẽ được đưa về cùng một luồng phụ để tính toán thống kê.
* **Tích lũy & Cắt cửa sổ (Window & Aggregation)**:
  * **Cửa sổ thời gian**: Cắt luồng dữ liệu theo các cửa sổ thời gian cố định 5 phút (Tumbling Window).
  * **Logic tính toán**: Đếm tổng số bài viết xuất hiện (`Count`) và phát hiện đột biến số lượng bài viết để xác định xu hướng.
* **Flink Sink**:
  * Đẩy kết quả thống kê thu gọn (ví dụ: `{"AI": 500}`) xuống cơ sở dữ liệu trung tâm **ClickHouse** (để vẽ đồ thị xu hướng lịch sử trên Dashboard) và ghi đè vào **Redis** (để hiển thị nhanh thời gian thực).
