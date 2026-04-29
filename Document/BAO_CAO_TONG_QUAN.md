# BÁO CÁO TỔNG QUAN HỆ THỐNG NOAH RETAIL UNIFIED COMMERCE

> **Mục đích:** Tài liệu này được biên soạn để tóm tắt toàn bộ kiến trúc, công nghệ và luồng xử lý của hệ thống. Đây là tài liệu cốt lõi giúp các thành viên trong nhóm ôn tập để **bảo vệ đồ án** trước giảng viên.

---

## 1. TỔNG QUAN DỰ ÁN
**NOAH Retail Unified Commerce** là một hệ thống tích hợp thương mại đa nền tảng. Mục tiêu của hệ thống là giải quyết bài toán phân mảnh dữ liệu giữa các cửa hàng Offline (quản lý bằng file CSV) và hệ thống bán hàng Online (Web Store). 

Hệ thống đảm bảo tính nhất quán dữ liệu từ lúc tiếp nhận đơn hàng, đồng bộ kho, chốt thanh toán, cho đến khi báo cáo doanh thu lên Dashboard cho ban giám đốc.

**Công nghệ lõi sử dụng:**
- **Ngôn ngữ:** Python 3.9+ (FastAPI, Streamlit)
- **Database:** MySQL 8.0 (Quản lý cửa hàng), PostgreSQL 15 (Quản lý tài chính).
- **Message Broker:** RabbitMQ (Xử lý hàng đợi bất đồng bộ).
- **API Gateway:** Kong Gateway (Bảo mật, điều phối traffic).
- **Infrastructure:** Docker & Docker Compose (Container hóa toàn bộ hệ thống).

---

## 2. KIẾN TRÚC HỆ THỐNG VÀ LUỒNG DỮ LIỆU (DATA FLOW)

Toàn bộ hệ thống được chia thành 6 phần (Module) kết nối lỏng lẻo (Loosely Coupled) với nhau:

1. **Khách hàng** gửi request mua hàng thông qua cổng bảo mật **Kong Gateway (Module 4)**.
2. Request đi vào **Order API (Module 2A)**. Tại đây API lưu đơn hàng vào **MySQL** với trạng thái `PENDING`, đồng thời đẩy một Message vào **RabbitMQ**.
3. **Order Worker (Module 2B)** liên tục lắng nghe RabbitMQ. Khi có message, nó sẽ:
   - Xử lý nghiệp vụ thanh toán (giả lập delay).
   - Ghi nhận giao dịch thành công vào **PostgreSQL**.
   - Cập nhật lại trạng thái đơn hàng bên **MySQL** thành `COMPLETED`.
4. Xuyên suốt quá trình đó, **Legacy Adapter (Module 1)** liên tục quét các file CSV từ các cửa hàng cũ để đẩy dữ liệu tồn kho lên MySQL.
5. Ban giám đốc xem báo cáo trên **Dashboard (Module 3)**. Dashboard này gọi dữ liệu từ Report API, API này tiến hành "Data Stitching" (nối dữ liệu) trực tiếp từ cả MySQL và PostgreSQL để ra được báo cáo hoàn chỉnh.
6. Trải nghiệm Khách hàng được cung cấp thông qua **Client Storefront (Module 5)**, một trang web HTML tĩnh phục vụ bằng Nginx giúp người dùng dễ dàng mua hàng bằng 1 click.

---

## 3. CHI TIẾT TỪNG MODULE (Dùng để trả lời Giảng Viên)

### Module 0: Infrastructure (Hạ tầng)
- **Vai trò:** Cung cấp môi trường chạy cho toàn bộ hệ thống bằng Docker Compose.
- **Câu hỏi thường gặp:** *"Tại sao lại dùng 2 Database khác nhau?"*
  - **Trả lời:** Theo triết lý Microservices (Polyglot Persistence), mỗi dịch vụ nên dùng DB phù hợp nhất. MySQL tốt cho Web Store (bán hàng), còn PostgreSQL có tính ACID cực mạnh nên rất phù hợp cho Finance (Tài chính).

### Module 1: Legacy Adapter (CSV Watchdog)
- **Vai trò:** Đọc các file CSV từ hệ thống cũ và đưa vào MySQL.
- **Điểm sáng kỹ thuật:** Hệ thống không bị crash nếu đọc trúng file CSV bị lỗi (Dirty Data). Nó bỏ qua dòng lỗi, ghi vào file Error Log và tiếp tục chạy.

### Module 2: Order Pipeline (Trái tim hệ thống)
- Được chia làm 2 phần: **Producer (API)** và **Consumer (Worker)**.
- **Câu hỏi thường gặp:** *"Tại sao không gọi API ghi thẳng vào Postgres mà phải qua RabbitMQ?"*
  - **Trả lời:** Để chịu tải (Load Leveling). Nếu có 10,000 người mua cùng lúc, API ghi thẳng vào DB sẽ làm sập DB. Việc dùng RabbitMQ làm "vùng đệm" giúp API trả về kết quả ngay lập tức (202 Accepted), còn DB sẽ được Worker từ từ ghi vào sau mà không bao giờ bị nghẽn.

### Module 3: Report & Dashboard
- **Vai trò:** Hiển thị biểu đồ doanh thu theo thời gian thực bằng Streamlit.
- **Điểm sáng kỹ thuật (Data Stitching):** Khác với code monolith (1 cục) JOIN 2 bảng trong 1 DB. Ở đây ta có 2 DB khác nhau. Report API dùng Python Pandas để lấy dữ liệu `orders` từ MySQL, lấy `transactions` từ Postgres, rồi dùng hàm `pd.merge()` để ghép chúng lại thông qua `order_id` ở tầng Application.

### Module 4: API Gateway (Kong)
- **Vai trò:** Đóng vai trò là người gác cổng duy nhất (`localhost:8000`).
- **Điểm sáng kỹ thuật:** 
  - Khách hàng không hề biết hệ thống có bao nhiêu service bên dưới.
  - Chống DDoS bằng `Rate Limiting` (10 request/phút).
  - Bảo mật bằng `Key-Auth` (Bắt buộc phải có `apikey` mới được đi qua).

### Module 5: Client Storefront (Option 5)
- **Vai trò:** Cung cấp giao diện trực quan cho Khách hàng (End-user) thao tác mua hàng. Trình diễn toàn bộ hệ thống từ đầu tới cuối (E2E).
- **Vị trí Code:** Nằm trong thư mục `Module5/storefront/` (File `index.html` và `Dockerfile`).
- **Điểm sáng kỹ thuật:** Tách biệt Frontend và Backend hoàn toàn (Micro-frontend). Sử dụng JavaScript `fetch()` gọi qua cửa ngõ Kong Gateway (Cổng 8000) kết hợp với cấu hình CORS (Cross-Origin Resource Sharing) chuẩn xác. Giao diện mượt mà không cần F5.

---

## 4. KỊCH BẢN DEMO KHI BẢO VỆ

Để có buổi bảo vệ hoàn hảo, hãy làm theo đúng thứ tự sau:

1. **Gõ lệnh khởi động:** `docker compose up -d` -> Show màn hình Docker Desktop xanh mượt.
2. **Mở trình duyệt (Trang Quản trị):** Mở `http://localhost:8501` để show giao diện Dashboard.
3. **Mở trình duyệt (Trang Cửa Hàng):** Mở `http://localhost:3000` (Module 5) để show giao diện bán hàng đẹp mắt cho người dùng cuối.
4. **Trình diễn Mua hàng bị chặn:** Dùng Postman hoặc Terminal (PowerShell) bắn thử 1 request vào API Order (Cổng 8000) **không kèm API Key** -> Show cho thầy cô thấy hệ thống Kong Gateway chặn truy cập trái phép.
   - *Cách làm (Dùng Terminal/PowerShell):* Mở Terminal lên và copy dán dòng lệnh này vào:
     `Invoke-RestMethod -Uri http://localhost:8000/api/orders -Method POST -ContentType "application/json" -Body '{"user_id": 1, "product_id": 1, "quantity": 1}'`
   - *Cách làm (Dùng Postman):* Tạo 1 request POST tới `http://localhost:8000/api/orders`, phần Body chọn `raw` -> `JSON` và điền `{"user_id": 1, "product_id": 1, "quantity": 1}`. Nhấn Send.
   - **Kết quả:** Màn hình sẽ báo lỗi màu đỏ `{"message":"No API key found in request"}` hoặc `401 Unauthorized`. Giảng viên sẽ rất ấn tượng vì bạn đã bảo mật thành công!
5. **Trình diễn Mua hàng thành công (End-to-End):** Quay lại trang Cửa Hàng (Cổng 3000), bấm nút "Mua Ngay". Trang này đã tự động nhúng API Key hợp lệ nên sẽ báo mua hàng thành công.
6. **Mở Dashboard:** Mở lại tab `http://localhost:8501` để chứng minh biểu đồ Doanh thu và Số đơn hàng tự động tăng lên nhờ hệ thống Worker và Data Stitching chạy hoàn hảo bên dưới. 

Chúc nhóm bảo vệ Đồ án thành công rực rỡ!
