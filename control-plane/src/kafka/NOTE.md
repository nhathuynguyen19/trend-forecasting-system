# 📝 Kafka Producer Guidelines

**Mục tiêu của module này:** Nhận payload chuẩn từ tầng `services` và đẩy an toàn vào hệ thống Kafka (topics crawl-tasks.{platform}) để giao việc cho cụm Crawlers. 

**Tuyệt đối KHÔNG viết business logic (validate, biến đổi dữ liệu...) ở đây.**

## 🎯 4 Yêu cầu cốt lõi khi code (Bắt buộc)

1. **Routing đúng Topic (Dynamic Topic):**
   - Không hardcode tên topic. Tên topic phải được build động theo format: `crawl-tasks.{platform}`.
   - *Ví dụ:* Lệnh crawl Reddit phải bay vào topic `crawl-tasks.reddit`.

2. **Gắn KEY cho Message (Quan trọng nhất):**
   - Kafka Message **BẮT BUỘC** phải có `Key`. 
   - `Key` = giá trị của trường `keyword` (VD: "Artificial Intelligence").
   - *Lý do:* Topic cấu hình Compacted. Việc gắn Key giúp Kafka biết đè lệnh mới lên lệnh cũ của cùng một từ khoá, và đảm bảo 1 từ khoá luôn được đẩy về cùng 1 Worker (Partition).

3. **Format Data (Message Value):**
   - Đóng gói dữ liệu thành JSON String.
   - Cấu trúc chuẩn: `{"keyword": "...", "since": "..."}`.

4. **Resilience & Lỗi (Xử lý Retry):**
   - Code Producer phải có cơ chế **Retry** (ít nhất 3 lần) và **Backoff**.
   - Phải bắt `try/catch`. Nếu Kafka rớt mạng, phải ném lỗi (Throw Error) ngược lại tầng HTTP/Service để báo cho Admin (UI) biết lệnh chưa được gửi. Không được "nuốt" lỗi (swallow exception).

## 💻 Mã giả định hướng (Pseudo-code Expectation)

```javascript
// Dù dùng ngôn ngữ như (Node, Go, Python), hàm gửi cần bám sát logic này:
async function dispatchCrawlTask(platform, taskPayload) {
    const topicName = `crawl-tasks.${platform}`;
    
    await kafkaProducer.send({
        topic: topicName,
        messages: [{
            key: taskPayload.keyword, // <--- BẮT BUỘC CÓ KEY
            value: JSON.stringify(taskPayload) // taskPayload là {"keyword": "...", "since": "..."}
        }],
        acks: 'all', // Đảm bảo không mất data
    });
}
