# Services Layer Guidelines

**Nhiệm vụ cốt lõi:** Đóng vai trò là "Bộ não" kiểm duyệt. Tiếp nhận dữ liệu thô từ HTTP API, làm sạch, chuẩn hóa và đưa ra quyết định giao việc. Tuyệt đối không chứa logic kết nối hạ tầng trực tiếp.

**Các quy tắc và điều kiện bắt buộc:**

1. **Kiểm duyệt đầu vào (Validation):**
   - Nền tảng (`platform`) phải nằm trong danh sách hệ thống hỗ trợ.
   - Từ khóa (`keyword`) không được rỗng và phải được cắt bỏ khoảng trắng thừa.
2. **Chuẩn hóa biến thời gian (Baseline Since):**
   - Biến thời gian nhận từ người dùng phải được đổi tên thống nhất thành `baseline_since`. Biến này chỉ đóng vai trò là "mốc thời gian giới hạn xa nhất" cho lần thu thập đầu tiên.
   - Bắt buộc ép kiểu `baseline_since` về định dạng chuẩn ISO 8601 UTC trước khi truyền đi để tránh sai lệch múi giờ giữa các cụm máy chủ.
3. **Chuyển giao (Delegation):**
   - Sau khi dữ liệu đã sạch, tầng Service chỉ được phép gọi hàm từ tầng Kafka để gửi lệnh đi. Không tự định nghĩa logic Kafka Producer tại đây.
   - Bắt lỗi và phân loại lỗi rõ ràng (ví dụ: lỗi do người dùng nhập sai vs lỗi hệ thống) để tầng API trả về HTTP Status Code phù hợp.
