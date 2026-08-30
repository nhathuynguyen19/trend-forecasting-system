# API Layer Guidelines

**Nhiệm vụ cốt lõi:** Đóng vai trò là "Cửa ngõ" (Controller) duy nhất giao tiếp với giao diện người dùng (Admin UI). Chịu trách nhiệm bóc tách dữ liệu từ HTTP Request, ủy quyền xử lý cho tầng Service, và định dạng HTTP Response trả về. 

**Tuyệt đối KHÔNG chứa business logic, KHÔNG tự validate nghiệp vụ sâu và KHÔNG kết nối trực tiếp với Kafka hay cơ sở dữ liệu tại tầng này.**

**Các quy tắc và điều kiện bắt buộc:**

1. **Nguyên tắc Thin Controller:**
   - Các hàm xử lý (Route handlers) chỉ được phép thực hiện đúng 3 bước: Trích xuất dữ liệu từ `req.body` ➔ Truyền nguyên trạng xuống cho hàm của thư mục `services` ➔ Nhận kết quả từ Service để gửi phản hồi (`res.json`).
   - Tầng này đóng vai trò "người đưa thư", mọi logic nhào nặn dữ liệu phải nhường lại cho Service.

2. **Bắt lỗi an toàn (Global Error Handling):**
   - Tất cả các endpoint bắt buộc phải được bọc trong khối `try/catch` hoặc thông qua một middleware xử lý lỗi tập trung.
   - Tuyệt đối không được để một request lỗi (do dữ liệu rác từ client hoặc do sập kết nối Kafka) làm sập (crash) toàn bộ tiến trình Control Plane.

3. **Quy chuẩn mã phản hồi (HTTP Status Codes):**
   - **Thành công:** Phải trả về mã `200 OK` (hoặc `201 Created`) kèm theo payload kết quả từ Service.
   - **Lỗi từ người dùng (Client Error):** Phải chủ động bắt các lỗi có định danh do tầng Service ném ra (ví dụ: lỗi trống từ khóa, lỗi sai nền tảng). Chuyển đổi các lỗi này thành mã `400 Bad Request` kèm thông báo rõ ràng để UI hiển thị.
   - **Lỗi hệ thống (Server Error):** Với các lỗi kết nối hạ tầng (Kafka rớt mạng) hoặc lỗi không xác định, bắt buộc phải log lại lỗi chi tiết vào hệ thống (console/file) và trả về cho client mã `500 Internal Server Error`. Tuyệt đối không rò rỉ chi tiết mã lỗi (stack trace) ra ngoài giao diện.

4. **Đồng nhất trường dữ liệu:**
   - Khi bóc tách `req.body`, phải đảm bảo lấy đủ 3 tham số từ giao diện: `platform`, `keyword`, và `since`. 
   - Tham số thời gian ở tầng này vẫn giữ tên là `since` (do giao diện truyền lên) và truyền thẳng xuống cho tầng Service. Việc chuẩn hóa và đổi tên thành `baseline_since` là trách nhiệm của Service, API không cần can thiệp.
