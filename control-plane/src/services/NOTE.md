# 📝 Services Layer Guidelines

**Mục tiêu của module này:** Đây là **"Bộ não" (Business Logic)** của hệ thống. Tầng này đứng giữa API (tiếp nhận HTTP Request) và Kafka (đẩy lệnh). Nhiệm vụ của nó là kiểm tra, làm sạch, chuẩn hoá dữ liệu và ra quyết định.

**Tuyệt đối KHÔNG dính líu đến HTTP Request (req, res) hay kết nối hạ tầng (Kafka/DB) trực tiếp ở đây.**

## 🎯 4 Yêu cầu cốt lõi khi code (Bắt buộc)

1. **Validation khắt khe (Kiểm duyệt đầu vào):**
   - Phải kiểm tra tính hợp lệ của `platform` (chỉ cho phép các nền tảng hệ thống đang hỗ trợ, vd: `reddit`, `facebook`).
   - `keyword` không được để trống, không được chứa ký tự đặc biệt gây lỗi.
   - `since` phải là một mốc thời gian hợp lệ (không được lớn hơn thời gian hiện tại).

2. **Chuẩn hoá dữ liệu (Normalization):**
   - `keyword`: Cần được `trim()` (cắt khoảng trắng 2 đầu) và chuẩn hoá viết hoa/thường tuỳ rule thống nhất.
   - `since`: BẮT BUỘC ép về chuẩn **ISO 8601 UTC** (VD: `2026-08-23T00:00:00Z`). Không lưu giờ Local để tránh lỗi khi Worker nằm ở timezone khác.

3. **Nguyên tắc "Gọi lại" (Delegation):**
   - Để đẩy lệnh đi, chỉ được phép `import` và gọi hàm từ thư mục `src/kafka/`. 
   - Không tự viết logic khởi tạo Kafka Producer ở tầng này.

4. **Bắn lỗi có ý nghĩa (Semantic Errors):**
   - Nếu validation thất bại, phải ném ra các Error có định danh rõ ràng (vd: `ValidationError`, `UnsupportedPlatformError`).
   - Tầng API sẽ bắt các lỗi này để trả về HTTP Status Code 400 (Bad Request) tương ứng cho Admin.

## 💻 Mã giả định hướng (Pseudo-code Expectation)

```javascript
// Nhiệm vụ của Services: Nhận data thô -> Xử lý -> Giao cho Kafka
const kafkaModule = require('../kafka/producer');

async function handleCrawlRequest(rawPlatform, rawKeyword, rawSince) {
    // 1. Validate
    if (!SUPPORTED_PLATFORMS.includes(rawPlatform)) {
        throw new Error(`Platform ${rawPlatform} is not supported.`);
    }
    if (!rawKeyword || rawKeyword.trim() === '') {
        throw new Error("Keyword cannot be empty.");
    }

    // 2. Normalize
    const cleanKeyword = rawKeyword.trim();
    const utcSinceDate = new Date(rawSince).toISOString();

    const taskPayload = {
        keyword: cleanKeyword,
        since: utcSinceDate
    };

    // 3. Dispatch to Kafka (Gọi sang thư mục kafka)
    await kafkaModule.dispatchCrawlTask(rawPlatform, taskPayload);

    // 4. Trả về kết quả cho tầng API
    return {
        status: "success",
        message: `Task for '${cleanKeyword}' dispatched to ${rawPlatform}`,
        dispatchedAt: new Date().toISOString()
    };
}
