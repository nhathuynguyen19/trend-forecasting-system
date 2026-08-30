# 📝 API Layer Guidelines (Tầng Tiếp nhận HTTP Request)

**Mục tiêu:** Đây là "Cửa ngõ" của hệ thống (Controller). Nhiệm vụ duy nhất của nó là tiếp nhận HTTP Request từ giao diện Admin (UI), bóc tách dữ liệu gửi xuống tầng `services`, và trả về HTTP Response cho người dùng. 

**Tuyệt đối KHÔNG chứa business logic, KHÔNG validate nghiệp vụ sâu và KHÔNG gọi trực tiếp hạ tầng (Kafka/DB) ở đây.**

## 🎯 3 Yêu cầu cốt lõi (Bắt buộc)

1. **Thin Controller (Controller siêu mỏng):** 
   - Hàm xử lý API (Route handler) chỉ nên dài tối đa 10-15 dòng.
   - Nhiệm vụ duy nhất: Lấy data từ `req.body` -> Gọi hàm của Service -> Trả kết quả `res.json()`.
   
2. **Chuẩn hoá HTTP Status Code:** 
   - Thành công: Trả về `200 OK` hoặc `201 Created`.
   - Lỗi từ người dùng (nhập sai): Bắt lỗi từ tầng Service và map thành `400 Bad Request`.
   - Lỗi hệ thống (Kafka sập): Bắt lỗi và map thành `500 Internal Server Error`.

3. **Global Error Handling (Bắt lỗi an toàn):**
   - Mọi route phải được bọc trong `try/catch` (hoặc dùng middleware gom lỗi). 
   - Tuyệt đối không được để một request lỗi làm sập (crash) toàn bộ server Control Plane.

## 💻 Mã giả định hướng (Express.js / Node.js style)

```javascript
// control-plane/src/api/taskController.js
const taskService = require('../services/taskService');

async function createCrawlTask(req, res, next) {
    try {
        // 1. Chỉ bóc tách dữ liệu từ HTTP Request
        const { platform, keyword, since } = req.body;

        // 2. Đẩy toàn bộ cho tầng Service lo liệu
        const result = await taskService.handleCrawlRequest(platform, keyword, since);

        // 3. Trả về Response thành công
        res.status(200).json(result);

    } catch (error) {
        // 4. Phân loại lỗi để trả về HTTP Status chuẩn
        if (error.message.includes("not supported") || error.message.includes("empty")) {
            // Lỗi do Admin nhập sai
            return res.status(400).json({ error: error.message });
        }
        
        // Lỗi hệ thống (Kafka lỗi mạng, lỗi code...)
        console.error("System Error:", error);
        res.status(500).json({ error: "Internal Server Error. Please try again later." });
    }
}

module.exports = { createCrawlTask };
