# Hướng Dẫn - Hộp Thư Trung Chuyển (kafka-infrastructure)

Thư mục này quản lý cấu hình và khởi tạo các ngăn tủ chứa tin nhắn (Topics/Partitions) trong Kafka.

---

## 1. Nhiệm Vụ Cốt Lõi

Đảm bảo hộp thư trung chuyển Kafka được cấu hình tối ưu để chịu tải lớn, không bị mất mát dữ liệu và phân phối tin nhắn song song mượt mà đến bộ máy đếm Flink.

---

## 2. Mô tả các Thư mục Con (Sẽ tạo sau)

* **`config/`** (Tệp cấu hình):
  * Chứa các tệp tin cấu hình cho các máy chủ Kafka (Brokers), thiết lập bộ nhớ đệm, thời gian lưu giữ tin nhắn (Retention time).
* **`topics/`** (Định nghĩa ngăn tủ chứa tin):
  * Chứa file mô tả cấu hình cho từng Topic. Ví dụ:
    * Topic `social.posts.raw` (chứa dữ liệu cào thô): Cấu hình 24 Partitions để Flink đọc song song.
    * Topic `crawl-tasks.{platform}` (chứa lệnh cào): Cấu hình Compacted Topic để tự động xóa các lệnh cũ, chỉ giữ lại lệnh mới nhất cho từng từ khóa.
* **`docker/`** (File đóng gói):
  * Chứa Dockerfile để tự đóng gói cụm máy chủ Kafka riêng nếu cần triển khai thực tế.
* **`scripts/`** (Script tự động):
  * Chứa mã bash tự khởi động và tạo sẵn các topic với số lượng partition mong muốn ngay khi bật Docker Compose lên (ví dụ: file `setup-kafka-topics.sh`).

---

## 3. Quy Tắc Cấu Hình Bắt Buộc

1. **Khớp nối 1:1**:
   * Số lượng Partitions của topic dữ liệu thô `social.posts.raw` bắt buộc phải cấu hình là **24** để khớp hoàn hảo với mức độ song song (Parallelism = 24) của Flink Processor, tránh việc nhiều luồng Flink tranh chấp đọc chung một partition.
2. **Hệ số an toàn (Replication Factor)**:
   * Trên môi trường chạy thực tế (Production/Kubernetes), hệ số nhân bản bắt buộc phải đặt bằng **3** (được quản lý bởi 3 broker khác nhau) để đảm bảo nếu 1 máy chủ Kafka bị sập, dữ liệu vẫn an toàn và hệ thống không bị gián đoạn.
