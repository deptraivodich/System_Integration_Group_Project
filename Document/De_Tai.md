ĐỒ ÁN NHÓM MÔN 
MÔN HỌC: CMU-CS 445 SYSTEM INTEGRATION PRACTICES
ĐỀ TÀI: XÂY DỰNG HỆ THỐNG "UNIFIED COMMERCE" CHO NOAH RETAIL
•	Hình thức: Nhóm 4-5 Sinh viên.
•	Thời gian thực hiện: 4 Tuần.
•	Mục tiêu: Vận dụng kiến thức từ Lab 1 đến Lab 6 để giải quyết bài toán doanh nghiệp thực tế.

1. BỐI CẢNH & "NỖI ĐAU" (THE STORY)
NOAH Retail là một chuỗi bán lẻ điện tử tầm trung tại Miền Trung, khởi nghiệp từ năm 2010. Sau 15 năm phát triển nóng, NOAH hiện sở hữu 5 cửa hàng vật lý và một kênh bán hàng Online (Web & App) đang tăng trưởng mạnh.
Tuy nhiên, hạ tầng CNTT của họ phát triển theo kiểu "chắp vá". Mỗi bộ phận mua sắm phần mềm riêng lẻ vào các thời điểm khác nhau, dẫn đến tình trạng "Ốc đảo dữ liệu" (Data Silos).
1.	Hệ thống Kho (Legacy Warehouse): Hệ thống cũ chạy AS/400. Không có API. Chỉ xuất được file CSV tồn kho (inventory.csv) vào lúc 3h sáng.
2.	Hệ thống Bán hàng (Web Store - MySQL): Website MySQL hiện đại. Tuy nhiên, do không kết nối với Kho, nó thường xuyên bán lố hàng (Overselling) vì không biết tồn kho thực tế
3.	Hệ thống Tài chính (Finance - PostgreSQL): Hệ thống mới chuyển đổi, nhân viên phải nhập liệu thủ công đơn hàng từ Web sang đây, gây chậm trễ.
Nhóm đóng vai trò là Solution Architects. Các bạn phải xây dựng một hệ thống Middleware (Trung gian) để tự động hóa dòng chảy dữ liệu giữa 3 hệ thống trên và xây dựng một Dashboard để chứng minh sự kết nối đó.

MODULE DỰ ÁN	NHIỆM VỤ CỤ THỂ	CÔNG CỤ / KỸ THUẬT	LAB THAM KHẢO	LECTURE LIÊN QUAN
0. Hạ Tầng	Dựng môi trường Docker chứa MySQL, Postgres, RabbitMQ, Kong.	Docker Compose, Networking.	Lab 1 (Container)	Lec 1: Intro & Heuristics (Independence).
1. Legacy Adapter	Quét file CSV từ kho, làm sạch dữ liệu và cập nhật vào MySQL.	File I/O, Batch Processing, Polling.	Lab 3 (File Transfer)	Lec 7: Integration Styles (File Transfer).
2. Order API	Tạo API POST /orders để nhận đơn hàng và gửi tin nhắn vào Queue.	Python FastAPI/Flask, REST API.	Lab 4 (RPC/Direct)	Lec 5: Services & SOA.
3. Middleware	Đọc tin nhắn từ Queue và ghi vào PostgreSQL.	RabbitMQ, Asynchronous Messaging.	Lab 5 (Messaging)	Lec 7 & 12: Middleware & Messaging.
4. Reporting	Tạo API GET /report gộp dữ liệu từ MySQL và Postgres.	Data Stitching (Join DBs), ETL.	Lab 2 (Data Int)	Lec 3 & 9: Data Integration.
5. Security	Cấu hình Gateway bảo vệ Dashboard.	Kong Gateway, API Key/JWT.	Lab 6 (Security)	Lec 10: Security & Gateway.
6. Dashboard	Code giao diện hiển thị dữ liệu đối soát & biểu đồ.	Streamlit (Python) hoặc Web Framework tùy chọn.	Case Study 5 LEC	Lec 3: Presentation Integration.
2. KIẾN TRÚC KỸ THUẬT YÊU CẦU (CORE REQUIREMENTS)
Nhóm phải thiết kế hệ thống chạy trên Docker Compose bao gồm các thành phần sau:
 TẦNG HẠ TẦNG (INFRASTRUCTURE)
•	MySQL 8.0: Lưu trữ dữ liệu Bán hàng (Web Store).
•	PostgreSQL 15: Lưu trữ dữ liệu Tài chính (Finance).
•	RabbitMQ 3: Message Broker trung chuyển tin nhắn.
•	Kong Gateway: Cổng bảo mật.
MODULE 1: ĐỒNG BỘ KHO (LEGACY ADAPTER)
Mục tiêu: Đồng bộ tồn kho từ hệ thống cũ (Legacy) sang hệ thống bán hàng hiện đại mà không làm treo hệ thống.
1. Đặc tả Đầu vào (Input)
•	Nguồn dữ liệu: Một thư mục trên ổ cứng (Volume) được chia sẻ với máy Host, ví dụ: /app/input.
•	Định dạng file: File CSV tên là inventory.csv được sinh ra ngẫu nhiên (bởi script admin_data_generator.py).
•	Cấu trúc dữ liệu: product_id, quantity (Ví dụ: 101, 50).
•	Tần suất: File có thể xuất hiện bất cứ lúc nào (giả lập việc hệ thống cũ xuất file định kỳ).
2. Yêu cầu Xử lý (Processing Logic)
1.	Cơ chế Polling: Service phải liên tục kiểm tra thư mục đầu vào (ví dụ: 5-10 giây/lần). Không được dùng cơ chế kích hoạt thủ công.
2.	Validate dữ liệu (Data Cleaning):
o	Nếu quantity < 0: Bỏ qua dòng đó, ghi log cảnh báo.
o	Nếu dòng thiếu dữ liệu hoặc sai định dạng: Bỏ qua.
3.	Cập nhật Database: Với mỗi dòng hợp lệ, thực hiện câu lệnh SQL UPDATE vào bảng products trong MySQL.
4.	Dọn dẹp (Cleanup): Sau khi xử lý xong, bắt buộc phải di chuyển file sang thư mục /app/processed.
3. Đặc tả Đầu ra (Output)
•	Database: Số lượng tồn kho trong MySQL thay đổi tương ứng.
•	File System: Thư mục /input rỗng, file xuất hiện bên /processed với tên cũ hoặc được đổi tên (ví dụ: inventory_timestamp.csv).
•	Log: Terminal hiển thị: [INFO] Processed 500 records. Skipped 5 invalid records.
 Gợi mở từ Lab cũ
•	Nhớ lại Lab 3 (File Transfer): Các em đã dùng thư viện os và shutil để quét và di chuyển file như thế nào?
•	Nhớ lại Lab 1 (Docker Volume): Làm sao để Container nhìn thấy file nằm trên máy thật của em? (Cấu hình volumes trong docker-compose.yml).
•	Vấn đề Dirty Data trong Lab 2: Xử lý try-catch khi đọc dữ liệu
•	
MODULE 2: XỬ LÝ ĐƠN HÀNG (ORDER PIPELINE)
Mục tiêu: Xử lý hàng nghìn đơn hàng cùng lúc mà không làm sập Database (High Availability), đảm bảo tính toàn vẹn dữ liệu (Data Consistency). Module này chia làm 2 thành phần nhỏ.
THÀNH PHẦN 2A: ORDER API (PRODUCER)
1. Đặc tả Đầu vào (Input)
•	Giao thức: HTTP POST.
•	Endpoint: /api/orders.
•	Payload JSON: {"user_id": 1, "product_id": 101, "quantity": 2}.
2. Yêu cầu Xử lý (Processing Logic)
1.	Validate: Kiểm tra dữ liệu đầu vào (số lượng phải > 0).
2.	Ghi nhận sơ bộ: Insert đơn hàng vào MySQL với trạng thái PENDING (Đang chờ xử lý).
3.	Publish: Đẩy toàn bộ cục JSON đơn hàng vào RabbitMQ (Queue tên: order_queue).
4.	Phản hồi nhanh: Trả về kết quả cho Client ngay lập tức, không chờ xử lý xong.
3. Đặc tả Đầu ra (Output)
•	HTTP Response: 202 Accepted hoặc 200 OK kèm {"message": "Order received", "order_id": 123}.
•	RabbitMQ: Queue có thêm 1 message mới.
THÀNH PHẦN 2B: ORDER WORKER (CONSUMER)
1. Đặc tả Đầu vào (Input)
•	Nguồn: Lắng nghe liên tục từ RabbitMQ Queue order_queue.
2. Yêu cầu Xử lý (Processing Logic)
1.	Consume: Lấy message ra khỏi hàng đợi.
2.	Giả lập độ trễ: Cho hệ thống ngủ (sleep) khoảng 1-2 giây để giả lập việc xử lý thanh toán phức tạp.
3.	Ghi hệ thống đích: Insert giao dịch vào PostgreSQL (Hệ thống Tài chính).
4.	Cập nhật trạng thái: Quay lại MySQL, update trạng thái đơn hàng từ PENDING sang COMPLETED (hoặc SYNCED).
5.	Acknowledge (ACK): Gửi xác nhận cho RabbitMQ để xóa tin nhắn (Đảm bảo tin nhắn không bị mất nếu Worker chết giữa chừng).
3. Đặc tả Đầu ra (Output)
•	MySQL: Đơn hàng đổi trạng thái.
•	PostgreSQL: Xuất hiện dòng dữ liệu mới.
•	RabbitMQ: Queue giảm đi 1 message.
Gợi mở từ Lab cũ
•	Nhớ lại Lab 4 (Direct API): Cách viết một API nhận POST Request bằng Flask/FastAPI?
•	Nhớ lại Lab 5 (Messaging):
o	Sự khác biệt giữa Code send.py (Producer) và receive.py (Consumer).
o	Tại sao trong Lab 5 chúng ta dùng pika?
o	Cơ chế ACK là gì? Nếu quên gửi ACK thì chuyện gì xảy ra với hàng đợi?
 MODULE 3: TRUNG TÂM CHỈ HUY (DASHBOARD)
Mục tiêu: Viết trang web dashboard tạo ra một "Góc nhìn toàn cảnh" (Single View) bằng cách ghép nối dữ liệu từ nhiều nguồn rời rạc (Data Stitching).
1. Đặc tả Đầu vào (Input)
•	Nguồn 1: Database MySQL (Thông tin chi tiết đơn hàng, Sản phẩm).
•	Nguồn 2: Database PostgreSQL (Thông tin thanh toán, Khách hàng).
2. Yêu cầu Xử lý (Processing Logic)
1.	Kết nối đa nguồn: Service này phải mở kết nối đồng thời đến cả MySQL và PostgreSQL .
2.	Query & Aggregation:
o	Lấy danh sách đơn hàng từ MySQL.
o	Lấy danh sách thanh toán từ Postgres.
3.	Data Stitching (Khâu dữ liệu): Dùng code (Python Pandas hoặc vòng lặp) để khớp 2 nguồn dữ liệu này dựa trên order_id.
4.	Tính toán: Tính tổng doanh thu theo từng khách hàng.
3. Đặc tả Đầu ra (Output)
•	API Endpoint: GET /api/report.
•	Format JSON:
Gợi mở từ Lab cũ
•	Nhớ lại Lab 2 (ETL):
o	Các em đã dùng pandas.read_sql để đọc từ SQLite. Bây giờ hãy đổi driver để đọc từ MySQL/Postgres.
o	Lệnh pd.merge dùng để làm gì? (Gợi ý: Giống VLOOKUP trong Excel hoặc JOIN trong SQL).
MODULE 4: BẢO MẬT (GATEWAY)
Mục tiêu: Ẩn giấu toàn bộ kiến trúc bên dưới, chỉ mở một cửa duy nhất cho người dùng.
1. Yêu cầu Cấu hình (Configuration)
•	Service & Route:
o	Map đường dẫn /orders -> Trỏ về Container Order API.
o	Map đường dẫn /report -> Trỏ về Container Report Service.
•	Plugins bắt buộc:
o	Key Authentication: Client phải gửi header apikey: noah-secret-key mới được đi qua.
o	Rate Limiting: Giới hạn mỗi Client chỉ được gửi tối đa 10 request/phút (Chống Spam).
o	CORS (Tùy chọn): Nếu làm Frontend riêng thì cần bật cái này.
2. Đặc tả Đầu ra (Output)
•	Truy cập http://localhost:8000/orders (Cổng Gateway) -> Thành công.
•	Truy cập http://localhost:5000/orders (Cổng trực tiếp của Service) -> Phải bị chặn (Không được expose port này trong docker-compose.yml).
 Gợi mở từ Lab cũ
•	Nhớ lại Lab 6 (API Gateway):
o	File kong.yml có cấu trúc thế nào?
o	Khái niệm Reverse Proxy: Tại sao Client không được biết IP thật của Backend?
o	Xem lại cách cấu hình services, routes và plugins trong Lab 6.

3. TÍNH ĐĂNG MỞ RỘNG 
 OPTION 1: NOTIFICATION SYSTEM (HỆ THỐNG THÔNG BÁO TỰ ĐỘNG)
Mục tiêu: Tăng trải nghiệm khách hàng bằng cách thông báo trạng thái đơn hàng tức thời (Real-time Feedback loop).
1. Kiến trúc tích hợp
•	Vị trí: Nằm sau Module 2B (Worker Service).
•	Trigger: Ngay sau khi Worker insert thành công vào PostgreSQL (Finance) và update trạng thái SYNCED cho MySQL.
2. Yêu cầu xử lý
•	Cơ chế: Worker không được bị "treo" để chờ gửi email. Việc gửi thông báo phải được thực hiện bất đồng bộ (Async) hoặc Fire-and-Forget.
•	Nội dung thông báo:
"Xin chào User [ID], đơn hàng #[Order_ID] trị giá $[Total] đã được xác nhận thanh toán thành công lúc [Time]."
•	Kênh gửi (Chọn 1):
o	Email: Sử dụng SMTP (Gmail/SendGrid/Mailgun).
o	Chat: Gửi tin nhắn vào Telegram Bot hoặc Slack Channel của nhóm (giả lập tin nhắn cho khách).
3. Tiêu chí nghiệm thu (Acceptance Criteria)
•	Có ảnh chụp Email/Tin nhắn nhận được trùng khớp với đơn hàng vừa đặt.
•	Log của Worker hiển thị: [INFO] Order #123 synced. Notification sent to user.
 OPTION 2: SMART OVERSELLING PROTECTION (CHỐNG BÁN LỐ BẰNG REDIS)
Mục tiêu: Giải quyết bài toán "High Concurrency" (Hàng nghìn người cùng tranh mua 1 sản phẩm). Database quan hệ (MySQL) sẽ bị chậm do khóa (Lock), dẫn đến bán lố.
1. Kiến trúc tích hợp
•	Công nghệ: Thêm 1 container Redis vào docker-compose.yml.
•	Vị trí: Nằm giữa Client và Module 2A (Order API).
2. Yêu cầu xử lý
•	Bước 1 (Sync): Khi Module 1 quét file CSV tồn kho, ngoài việc update MySQL, nó phải nạp (set) số lượng tồn kho vào Redis Key (Ví dụ: product:101:stock = 50).
•	Bước 2 (Check): Khi có Request đặt hàng:
o	API KHÔNG query MySQL để check tồn kho.
o	API gọi lệnh DECR (Decrement Atomic) trong Redis.
o	Nếu giá trị trả về >= 0 -> Đẩy vào Queue RabbitMQ.
o	Nếu giá trị trả về < 0 -> Trả về lỗi 400 Out of Stock ngay lập tức.
o	Lý do: Redis xử lý trên RAM, tốc độ nhanh gấp 100 lần MySQL.
3. Tiêu chí nghiệm thu
•	Chứng minh được trường hợp: Tồn kho = 1. Gửi 5 request đồng thời (bằng JMeter hoặc Postman Runner). Chỉ 1 request thành công, 4 request kia bị từ chối. Tồn kho trong Redis về 0.
 OPTION 3: AI INSIGHT (PHÂN TÍCH DOANH THU THÔNG MINH)
Mục tiêu: Biến Dashboard từ "Báo cáo chết" thành "Trợ lý ảo".
1. Kiến trúc tích hợp
•	Vị trí: Nằm trong Module 3 (Report Service).
•	Integration: Gọi API của bên thứ 3 (OpenAI GPT-3.5/4 hoặc Google Gemini).
2. Yêu cầu xử lý
•	Input: Service tổng hợp số liệu (Ví dụ: "Tổng doanh thu hôm nay: 50 triệu. Top sản phẩm: Giày Nike. Tỷ lệ đơn lỗi: 2%").
•	Prompt Engineering: Gửi đoạn text trên cho AI với yêu cầu: "Đóng vai chuyên gia tài chính, hãy nhận xét ngắn gọn về tình hình kinh doanh này và đưa ra 1 lời khuyên."
•	Output: Hiển thị đoạn văn trả lời của AI lên Dashboard.
3. Lưu ý quan trọng
•	Cấm: Không được gửi toàn bộ danh sách 20,000 đơn hàng lên AI (tốn tiền và lộ dữ liệu). Chỉ gửi số liệu đã tổng hợp (Aggregated Data).
•	Failover: Nếu API AI bị lỗi (hết quota), Dashboard vẫn phải hiện số liệu bình thường.
 OPTION 4: REAL-TIME DASHBOARD (WEBSOCKET)
Mục tiêu: Loại bỏ thao tác nhấn F5 để xem dữ liệu mới.
1. Kiến trúc tích hợp
•	Công nghệ: WebSocket (Socket.io hoặc Python Websockets).
•	Vị trí: Kết nối 2 chiều giữa Dashboard (Frontend) và Backend.
2. Yêu cầu xử lý
•	Cơ chế Pub/Sub:
o	Khi Module 2A nhận đơn hàng mới -> Phát sự kiện (Emit) new_order.
o	Dashboard đang lắng nghe sự kiện new_order -> Tự động tăng biến đếm "Số đơn chờ xử lý" +1.
o	Hiệu ứng UI: Con số nhấp nháy hoặc đổi màu khi cập nhật.
3. Tiêu chí nghiệm thu
•	Mở Dashboard trên 1 màn hình.
•	Dùng Postman bắn đơn hàng liên tục.
•	Số trên Dashboard tự nhảy múa mà không cần reload trang.

 OPTION 5: CLIENT STOREFRONT (TRANG KHÁCH HÀNG)
Mục tiêu: Mô phỏng trọn vẹn quy trình E-commerce (End-to-End).
1. Kiến trúc tích hợp
•	Vị trí: Container Frontend riêng biệt (chạy React/Vue/Angular hoặc HTML thuần), map port 3000.
•	Flow: Client Storefront -> Gọi qua Kong Gateway -> Vào Order API.
2. Yêu cầu xử lý
•	Giao diện:
o	Trang chủ: Load danh sách sản phẩm từ API (Lấy từ MySQL).
o	Có nút "Add to Cart" hoặc "Buy Now".
o	Form nhập thông tin User.
•	UX: Khi bấm mua -> Hiện Loading -> Hiện thông báo thành công "Cảm ơn bạn đã mua hàng".
3. Tiêu chí nghiệm thu
•	Demo quy trình mua hàng mượt mà trên trình duyệt thay vì thao tác bằng dòng lệnh/Postman.
LỜI KHUYÊN CHO SINH VIÊN KHI CHỌN 
•	Nhóm mạnh về thuật toán/Backend: Nên chọn Smart Overselling (Redis). Đây là bài toán khó và "ghi điểm" cực mạnh trong mắt nhà tuyển dụng Backend.
•	Nhóm mạnh về Frontend/Sản phẩm: Nên chọn Client Storefront hoặc Real-time Socket.
•	Nhóm thích xu hướng mới: Chọn AI Insight.
________________________________________
4. TÀI NGUYÊN & HỖ TRỢ (STARTER KIT)
1.	Script sinh dữ liệu: admin_data_generator.py (Dùng để tạo file SQL 20.000 đơn hàng và file CSV rác để test).
2.	Code mẫu: Các đoạn code kết nối DB cơ bản (Python/SQLAlchemy).
3.	Lời khuyên: Đừng chỉ copy-paste code Lab cũ. Hãy dùng chúng làm nền tảng và nâng cấp chúng lên mức "Production-ready" (Xử lý lỗi, Retry connection, Log file).
CÁC THỬ THÁCH KỸ THUẬT (CHALLENGES)
1.	Dữ liệu lớn (Pagination Challenge):
o	Bảng Orders có sẵn 20,000 dòng.
o	Cấm: Code Dashboard/API dùng SELECT * (sẽ bị treo).
o	Yêu cầu: Phải dùng kỹ thuật Phân trang (LIMIT, OFFSET).
2.	Dữ liệu bẩn (Dirty Data Challenge):
o	File CSV chứa 5% dữ liệu lỗi.
o	Nếu Service Import bị dừng hoạt động khi gặp dòng lỗi => Trừ 50% điểm Module 1.
o	Yêu cầu: Code không được crash (dừng chạy). Phải ghi log lỗi và tiếp tục chạy.
3.	Khởi động lạnh (Retry Challenge):
o	Database khi khởi động mất 10-20s. Code Python chạy lên ngay sẽ bị lỗi kết nối.
o	Yêu cầu: Viết hàm retry_connection() (thử lại sau 5s) để Service tự phục hồi.

5. MA TRẬN ĐÁNH GIÁ (GRADING RUBRIC)
HẠNG MỤC	TRỌNG SỐ	TIÊU CHÍ CHI TIẾT
1. LOGIC TÍCH HỢP	3.0 đ	- Dữ liệu chảy đúng luồng: CSV -> MySQL -> RabbitMQ -> Postgres. 
- Code API và Worker tách biệt rõ ràng.
2. HẠ TẦNG (DEVOPS)	2.0 đ	- Docker Compose chuẩn, chạy được ngay ("docker-compose up"). 
- Các service nhìn thấy nhau bằng tên (DNS), không hard-code IP.
3. DASHBOARD & UI/UX	2.0 đ	- Giao diện trực quan, chuyên nghiệp (hơn mức basic). 
- Có chức năng phân trang (Pagination) cho dữ liệu lớn. 

- Chứng minh được sự khớp lệnh dữ liệu.
4. SÁNG TẠO & GIÁ TRỊ	2.0 đ	- Có triển khai tính năng trong "Thực đơn sáng tạo". 
- Hoặc giải quyết bài toán nghiệp vụ thông minh. 
- (Điểm thưởng thêm nếu tích hợp MongoDB Audit Log )
5. ĐỘ BỀN VỮNG	1.0 đ	- Hệ thống không "chết" khi gặp file CSV rác. 
- Có cơ chế tự thử lại (Retry) khi Database khởi động chậm.
TỔNG CỘNG	10.0	
________________________________________
LỊCH TRÌNH NỘP BÀI
1.	Tuần 1: Nộp Sơ đồ kiến trúc & Phân công nhóm.
2.	Tuần 4: Nộp Source Code (Git), Video Demo và Báo cáo Tổng kết (Portfolio).
3.	LỜI KHUYÊN: Đồ án này là sự tổng hợp của 6 bài Lab. Hãy mở lại code Lab cũ, copy các đoạn xử lý File, xử lý Queue và ghép chúng lại. Chúc các nhóm thành công!



================================================================================
lab tham khảo làm dự án(nhóm đã được làm những bài lab này như những phần riêng lẻ cho bài nhóm chỉ có điều là đề tài khác của bài nhóm)

LAB 1: THE CONTAINER - CHUẨN HÓA MÔI TRƯỜNG 
A. THÔNG TIN CHUNG (META INFO) 
•	Môn học: CMU-CS 445 System Integration Practices. 
•	Ánh xạ kiến thức: Lecture 1 (Introduction) - Heuristic "Simplify & Independence". 
•	Thời lượng ước tính: 60 phút. • 	Cấp độ: Cơ bản (Foundation). 
 
B. MỤC TIÊU & BỐI CẢNH (OBJECTIVES & SCENARIO) 
1. Kịch bản (Scenario) 
Bạn là nhân viên mới gia nhập đội dự án NOAH Retail. Team Leader gửi cho bạn một đoạn code Python và nói: "Chạy cái này đi". 
Tuy nhiên, khi bạn chạy trên máy mình, nó báo lỗi thiếu thư viện, sai phiên bản Python, và xung đột với các phần mềm khác. Đây là vấn đề kinh điển: "It works on my machine" (Nó chạy trên máy tôi mà!). 
Nhiệm vụ của bạn là sử dụng công nghệ Containerization (Docker) để đóng gói ứng dụng này thành một khối độc lập, đảm bảo nó chạy giống hệt nhau trên máy bạn, máy Sếp và máy chủ. 
2. Mục tiêu kỹ thuật 
•	Hiểu cơ chế Isolation (Cô lập môi trường). 
•	Hiểu tính chất Immutability (Bất biến) của Image. 
•	Thành thạo các lệnh: docker build, docker run, docker ps. 
3. Sơ đồ kiến trúc (Architecture) 
Chúng ta sẽ biến ứng dụng Python thành một Container nằm gọn trên nền Docker Host. 
C. CHUẨN BỊ (PREREQUISITES) 
1.	Phần mềm: o 	Docker Desktop (đã cài đặt và đang chạy - biểu tượng cá voi màu xanh/trắng). 
o	VS Code (hoặc bất kỳ Text Editor nào). o 	Postman (hoặc trình duyệt Chrome/Edge). 
2.	Tài nguyên: 
o	Tạo một thư mục rỗng trên máy tính tên là: Lab1_Container. 
 
D. CÁC BƯỚC THỰC HIỆN (STEP-BY-STEP) 
 TASK 1: KHỞI TẠO ỨNG DỤNG MẪU 
Mục đích: Tạo ra một web service đơn giản để làm chuột bạch thí nghiệm. 
Bước 1.1: Mở VS Code tại thư mục Lab1_Container. 
Bước 1.2: Tạo file app.py với nội dung sau: 
Python 
# app.py import os import socket 
from flask import Flask, jsonify 
 
app = Flask(__name__) 
 
@app.route('/') def info(): 
    # Lấy Hostname để xem code đang chạy trên máy nào (Máy thật hay Container) 
    container_id = socket.gethostname() 
     
    # Lấy biến môi trường (Config) từ bên ngoài truyền vào     env_name = os.getenv('ENV_NAME', 'Local Environment') 
 
    return jsonify({ 
        "status": "Success", 
        "message": "Hello from System Integration Class!", 
        "running_on_container_id": container_id, 
        "environment_config": env_name 
    })  if __name__ == '__main__': 
    # host='0.0.0.0' là BẮT BUỘC để container mở cửa cho bên ngoài truy cập 
    app.run(host='0.0.0.0', port=5000) 
 
Bước 1.3: Tạo file requirements.txt (Danh sách thư viện cần thiết): 
 
flask 
 
TASK 2: VIẾT CÔNG THỨC ĐÓNG GÓI (DOCKERFILE) 
Mục đích: Định nghĩa môi trường tiêu chuẩn cho ứng dụng. 
Bước 2.1: Tạo file tên là Dockerfile (Lưu ý: Chữ D viết hoa, không có đuôi mở rộng). 
Bước 2.2: Nhập nội dung sau: 
Dockerfile 
 
# 1. Chọn hệ điều hành nền (Base Image) 
# Dùng bản Python 3.9 rút gọn (slim) để nhẹ máy 
FROM python:3.9-slim 
 
# 2. Thiết lập thư mục làm việc bên trong Container 
WORKDIR /app 
 
# 3. Copy file thư viện vào trước (Tối ưu Cache) COPY requirements.txt . 
 
# 4. Cài đặt thư viện 
RUN pip install --no-cache-dir -r requirements.txt 
 
# 5. Copy toàn bộ code nguồn vào Container COPY . . 
 
# 6. Khai báo cổng sẽ sử dụng (Optional) 
EXPOSE 5000 
 
# 7. Lệnh chạy mặc định khi Container khởi động 
CMD ["python", "app.py"] 
 
Giải thích cơ chế: 
Dockerfile giống như một "Tờ hướng dẫn lắp ráp". Khi đưa tờ giấy này cho Docker Engine, nó sẽ tự động tải OS, cài Python, cài Flask mà không cần bạn can thiệp thủ công. 
 
TASK 3: ĐÓNG GÓI (BUILD IMAGE) 
Mục đích: Biến code + môi trường thành một file ảnh (Image) duy nhất. Bước 3.1: Mở Terminal (trong VS Code), gõ lệnh: 
Bash 
 
docker build -t lab1-integration-image . 
 
(Lưu ý dấu chấm . ở cuối lệnh, nghĩa là "build tại thư mục hiện tại"). 
Bước 3.2: Kiểm tra xem Image đã được tạo chưa: Bash 
docker images 
 
Kết quả kỳ vọng: Thấy dòng lab1-integration-image xuất hiện trong danh sách. 
 
TASK 4: CHẠY THỬ & KIỂM CHỨNG (RUN & VERIFY) 
Mục đích: Chứng minh tính "Độc lập" (Independence) bằng cách chạy 2 bản sao khác nhau. 
Bước 4.1: Chạy Container số 1 (Mô phỏng Server Alpha): 
Bash 
 
docker run -d -p 5001:5000 --name sv_alpha -e ENV_NAME="ALPHA SERVER" lab1-integration-image 
 
Bước 4.2: Chạy Container số 2 (Mô phỏng Server Beta): 
Bash 
 
docker run -d -p 5002:5000 --name sv_beta -e ENV_NAME="BETA SERVER" lab1-integration-image 
 
Bước 4.3: Kiểm tra trên trình duyệt. 
•	Mở: http://localhost:5001 -> Bạn sẽ thấy "environment_config": "ALPHA SERVER". 
•	Mở: http://localhost:5002 -> Bạn sẽ thấy "environment_config": "BETA SERVER". 
 Giải thích cơ chế: 
Hãy nhìn vào trường "running_on_container_id". Bạn sẽ thấy 2 chuỗi ký tự khác nhau. Điều này chứng tỏ 2 ứng dụng đang chạy trên 2 "máy ảo" (container) hoàn toàn biệt lập, dù chúng chung một Source Code. 
E. THỬ THÁCH NÂNG CAO (CHALLENGE - 20% ĐIỂM) 
Phần này sinh viên phải tự suy luận để thực hiện. 
Mục tiêu: Hiểu về tính Bất biến (Immutability). 
1.	Hành động: Quay lại VS Code, mở file app.py, sửa dòng chữ "Hello from System 
Integration Class!" thành "Version 2.0 Updated". Lưu file lại. 
2.	Kiểm tra: Quay lại trình duyệt (localhost:5001), bấm Refresh (F5). 
3.	Quan sát: Nội dung trên web có thay đổi không? (Đáp án là KHÔNG). 
4.	Nhiệm vụ: Hãy thực hiện các lệnh cần thiết để nội dung mới xuất hiện trên trình duyệt (Gợi ý: Phải Build lại Image và Run lại Container mới). 
5.	Báo cáo: Chụp ảnh màn hình kết quả "Version 2.0 Updated" và dán vào bài thu hoạch. 
 
F. YÊU CẦU NỘP BÀI (SUBMISSION) 
Sinh viên nộp 1 file nén  BÁO CÁO PDF bao gồm: 
1.	Báo cáo (PDF): Theo mẫu Standard Submission Template đã cung cấp. 
o 	Ảnh chụp Terminal khi Build thành công. o 	Ảnh chụp trình duyệt hiển thị kết quả Alpha và Beta. o 	Giải thích ngắn gọn ý nghĩa các dòng trong Dockerfile. o 	Trả lời 5 câu hỏi Neo kiến thức (trong mẫu báo cáo). 
2.	Source Code: Thư mục chứa app.py, Dockerfile, requirements.txt. 
Hạn nộp: [Ngày/Giờ] trên hệ thống LMS. 
 
LAB 2: DATA INTEGRATION - THE ETL PIPELINE 
A. THÔNG TIN CHUNG (META INFO) 
•	Môn học: CMU-CS 445 System Integration Practices. 
•	Ánh xạ kiến thức: Lecture 3 (Data Integration) - Data Warehousing & ETL. 
•	Thời lượng ước tính: 75 phút. 
•	Cấp độ: Trung bình (Intermediate). 
 
B. MỤC TIÊU & BỐI CẢNH (OBJECTIVES & SCENARIO) 
1. Kịch bản (Scenario) 
Phòng Marketing của NOAH Retail đang cần danh sách "Top Khách hàng chi tiêu nhiều nhất" để gửi quà tri ân. 
Tuy nhiên, dữ liệu đang nằm rải rác ở 2 nơi: 
1.	Thông tin cá nhân (Tên, Email): Nằm trong một file Text cũ (customers.csv) xuất từ hệ thống CRM. 
2.	Lịch sử giao dịch: Nằm trong Database bán hàng (orders.db - SQLite). 
Nếu làm thủ công, bạn phải mở Excel lên và VLOOKUP rất vất vả. Nhiệm vụ của bạn là viết một chương trình Python tự động hóa quy trình này: Đọc dữ liệu từ 2 nguồn khác nhau -> Gộp lại -> Tính toán tổng chi tiêu. 
2.	Mục tiêu kỹ thuật • 	Hiểu quy trình ETL: Extract (Trích xuất) -> Transform (Xử lý) -> Load (Tải ra). 
•	Sử dụng thư viện Pandas để xử lý dữ liệu dạng bảng. 
•	Kỹ thuật Data Stitching: Ghép nối dữ liệu từ các nguồn không đồng nhất (Heterogeneous Sources). 
3.	Sơ đồ kiến trúc (Architecture) 
 
C. CHUẨN BỊ (PREREQUISITES) 
1.	Môi trường: Đã cài đặt Docker và VS Code. 
2.	Tài nguyên: Tạo thư mục Lab2_ETL trên máy tính. 
 
D. CÁC BƯỚC THỰC HIỆN (STEP-BY-STEP) 
TASK 1: CHUẨN BỊ DỮ LIỆU GIẢ LẬP (PREPARE DATA) 
Mục đích: Tạo ra 2 nguồn dữ liệu rời rạc để thực hành ghép nối. 
Bước 1.1: Trong thư mục Lab2_ETL, tạo file customers.csv (Nguồn 1): Code  
 
id,name,email 
1,Nguyen Van A,anv@gmail.com 
2,Tran Thi B,btt@yahoo.com 
3,Le Van C,cle@hotmail.com 
4,Pham Van D,dpham@gmail.com 
 
Bước 1.2: Tạo file init_db.py để sinh Database SQLite (Nguồn 2): 
Python 
 
import sqlite3 
 
# Tạo file database giả lập conn = sqlite3.connect('orders.db') c = conn.cursor() 
 
# Tạo bảng Orders 
c.execute('''CREATE TABLE orders 
             (order_id INTEGER PRIMARY KEY, customer_id INTEGER, amount REAL)''')  
# Insert dữ liệu mẫu (Khách hàng 1 mua 2 lần, Khách 2 mua 1 lần, Khách 3 không mua) data = [ 
    (101, 1, 500.0), 
    (102, 1, 300.0), 
    (103, 2, 1200.0), 
    (104, 4, 150.0) 
] 
c.executemany('INSERT INTO orders VALUES (?,?,?)', data)  conn.commit() conn.close() 
print("Database orders.db created successfully!") 
 
Bước 1.3: Chạy file này một lần để tạo file .db: 
(Nếu máy chưa cài Python, bạn có thể bỏ qua bước chạy này, chúng ta sẽ để Docker chạy nó sau). 
TASK 2: VIẾT ETL SCRIPT (THE INTEGRATOR) 
Mục đích: Viết logic "Trái tim" của hệ thống tích hợp. 
Tạo file etl_script.py với nội dung sau: 
Python 
 
import pandas as pd import sqlite3 import os 
 def run_etl(): 
    print(" STARTED ETL PROCESS...") 
 
    # --- PHASE 1: EXTRACT (Trích xuất) --- 
    print("[1] Extracting data from heterogeneous sources...")      
    # Nguồn 1: Đọc file CSV     try: 
        df_customers = pd.read_csv('customers.csv') 
        print(f"   -> Loaded {len(df_customers)} customers from CSV.")     except Exception as e: 
        print(f"Error reading CSV: {e}")         return 
 
    # Nguồn 2: Đọc SQL Database     try: 
        conn = sqlite3.connect('orders.db') 
        df_orders = pd.read_sql_query("SELECT * FROM orders", conn)         print(f"   -> Loaded {len(df_orders)} orders from SQLite.")     except Exception as e: 
        print(f"Error reading DB: {e}")         return     finally: 
        if conn: conn.close() 
 
    # --- PHASE 2: TRANSFORM (Xử lý & Gộp) ---     print("[2] Transforming data...") 
 
    # Bước 2.1: Join 2 bảng lại với nhau dựa trên ID     # (Tương tự VLOOKUP trong Excel hoặc JOIN trong SQL) 
    merged_df = pd.merge(df_orders, df_customers, left_on='customer_id', right_on='id', how='left') 
 
    # Bước 2.2: Tính tổng tiền chi tiêu theo từng khách     report_df = merged_df.groupby(['name', 
'email'])['amount'].sum().reset_index() 
     
    # Bước 2.3: Đổi tên cột cho đẹp 
    report_df.columns = ['Customer Name', 'Email', 'Total Spent']  
    # --- PHASE 3: LOAD (Tải ra báo cáo) ---     print("[3] Loading Data to Report...")     print("\n--- FINAL REPORT ---")     print(report_df) 
     
    # Xuất ra file kết quả 
    report_df.to_csv('final_report.csv', index=False) 
    print("\n Report saved to 'final_report.csv'") 
 if __name__ == "__main__": 
    # Kiểm tra xem DB có tồn tại chưa, nếu chưa thì tạo (cho trường hợp chạy Docker lần đầu)     if not os.path.exists('orders.db'): 
        import init_db # Tự động chạy script tạo DB nếu chưa có     run_etl() 
 
Giải thích cơ chế: 
•	pd.read_csv và pd.read_sql: Là các "Adapter" giúp Python hiểu được dữ liệu từ 2 định dạng khác nhau. 
•	pd.merge: Là kỹ thuật "Data Stitching" (Khâu dữ liệu). Nó tìm các bản ghi có chung ID và ghép chúng lại thành một dòng duy nhất. 
TASK 3: ĐÓNG GÓI MÔI TRƯỜNG (DOCKERIZE) 
Mục đích: Đảm bảo script chạy được trên mọi máy mà không cần cài Pandas thủ công. 
Tạo file Dockerfile: 
Dockerfile 
 
# Sử dụng Python Slim 
FROM python:3.9-slim 
 
WORKDIR /app 
 
# Cài đặt thư viện Pandas (Xử lý dữ liệu) 
# Lưu ý: Cài pandas sẽ hơi lâu (1-2 phút) 
RUN pip install pandas sqlalchemy 
 
# Copy toàn bộ code vào COPY . . 
 
# Chạy script tạo DB trước, sau đó chạy ETL 
CMD ["python", "etl_script.py"] 
 
TASK 4: CHẠY VÀ KIỂM TRA 
Mục đích: Thực thi quy trình. 
Bước 4.1: Build Image 
Bash 
 
docker build -t lab2-etl . 
 
Bước 4.2: Run Container 
Bash 
 
docker run --name etl_worker lab2-etl 
 
Bước 4.3: Kiểm tra kết quả trên Terminal. Bạn sẽ thấy bảng báo cáo hiện ra: 
 
   Customer Name            Email  Total Spent 
0	Le Van C    cle@hotmail.com          NaN  <-- (Nếu dùng LEFT JOIN mà khách ko mua) 
1	Nguyen Van A    anv@gmail.com        800.0 
2	Pham Van D  dpham@gmail.com        150.0 
3	Tran Thi B    btt@yahoo.com       1200.0 
 
E. THỬ THÁCH NÂNG CAO (CHALLENGE - 20% ĐIỂM) 
Tình huống: Sếp không quan tâm đến những khách hàng "tiềm năng" (chưa mua gì) hoặc mua quá ít. 
Yêu cầu: 1. Sửa file etl_script.py. 
2.	Thêm logic lọc: Chỉ hiển thị những khách hàng có Total Spent > 500. 
3.	Sắp xếp danh sách theo số tiền giảm dần (Người giàu nhất đứng đầu). 
4.	Build lại Image và chạy lại. 
Kết quả mong đợi: Báo cáo chỉ còn lại 2 người: Tran Thi B (1200.0) và Nguyen Van A (800.0). 
 
F. HƯỚNG DẪN NỘP BÀI (SUBMISSION) 
Sinh viên nộp file  Submission_RP2 gồm: 
1.	Báo cáo PDF: 
o	Ảnh chụp Terminal kết quả chạy Task 4 (Bảng dữ liệu chưa lọc). 
o	Ảnh chụp Terminal kết quả phần Challenge (Bảng dữ liệu đã lọc > 500). o 	Giải thích ý nghĩa lệnh pd.merge trong code. 
2.	Source Code: etl_script.py, customers.csv, Dockerfile. 

LAB 3: LEGACY INTEGRATION - FILE TRANSFER 
PATTERN 
A. THÔNG TIN CHUNG (META INFO) 
•	Môn học: CMU-CS 445 System Integration Practices. 
•	Ánh xạ kiến thức: Lecture 7 (Integration Styles) - File Transfer & Shared Database. 
•	Thời lượng ước tính: 75 phút. 
•	Cấp độ: Trung bình (Intermediate). 
 
B. MỤC TIÊU & BỐI CẢNH (OBJECTIVES & SCENARIO) 
1.	Kịch bản (Scenario) Hệ thống Kho của NOAH Retail là một phần mềm cũ chạy trên máy chủ AS/400 (từ năm 2010). Nó không có API (không REST, không SOAP). Cách duy nhất nó giao tiếp với thế giới bên ngoài là xuất ra một file inventory.csv vào lúc 3:00 sáng hàng ngày vào một thư mục chia sẻ (FTP Folder). 
Nhiệm vụ của bạn là viết một "Watchdog Service" (Chú chó canh cửa): 
1.	Ngồi canh thư mục đó 24/7. 
2.	Ngay khi thấy file CSV xuất hiện -> "Vồ" lấy nó ngay. 
3.	Đọc dữ liệu -> Xử lý (Validate). 
4.	Cất file đi chỗ khác (/processed) để không xử lý nhầm lần hai. 
2.	Mục tiêu kỹ thuật • 	Hiểu cơ chế Polling (Vòng lặp quét sự kiện). 
•	Xử lý File Lifecycle (New -> Processing -> Processed/Error). 
•	Kỹ thuật Docker Volumes để giả lập thư mục chia sẻ (Shared Folder) giữa Host và Container. 
3.	Sơ đồ kiến trúc (Architecture) 
 
C. CHUẨN BỊ (PREREQUISITES) 
1.	Môi trường: Docker Desktop, VS Code. 
2.	Tài nguyên: Tạo thư mục Lab3_FileTransfer trên máy tính. Trong đó tạo sẵn 3 thư mục con rỗng: 
o	input/ (Nơi file CSV sẽ xuất hiện). 
o	processed/ (Nơi cất file đã làm xong). o error/ (Nơi vứt file bị lỗi). 
 
D. CÁC BƯỚC THỰC HIỆN (STEP-BY-STEP) 
 TASK 1: CHUẨN BỊ DỮ LIỆU MẪU 
Mục đích: Tạo thủ công một file CSV để giả lập việc hệ thống Kho xuất dữ liệu. Bước 1.1: Mở Notepad/VS Code, tạo file data_2024.csv với nội dung:  
sku,qty,warehouse TV-SONY-55,10,DN 
IPHONE-15,5,HN 
FRIDGE-LG,-5,HCM  <-- (Dòng lỗi: Số lượng âm) 
LAPTOP-DELL,20,DN 
(Lưu ý: Đừng vội bỏ file này vào thư mục input. Hãy để nó ở ngoài). 
 
TASK 2: VIẾT WATCHDOG SCRIPT (PYTHON) 
Mục đích: Viết logic xử lý File. 
Bước 2.1: Tạo file watcher.py trong thư mục gốc Lab3_FileTransfer. 
Python 
 
import os import time import shutil import csv 
 
# Cấu hình đường dẫn (Path) 
INPUT_DIR = './input' 
PROCESSED_DIR = './processed' 
ERROR_DIR = './error' 
 def process_file(filepath): 
    print(f"⚡ Found new file: {filepath}")     filename = os.path.basename(filepath) 
         try:         with open(filepath, 'r') as f:             reader = csv.DictReader(f)             print("   --- READING DATA ---")             for row in reader:                 sku = row['sku'] 
                qty = int(row['qty']) # Có thể gây lỗi nếu qty không phải số 
                 
                # Validation Logic (Kiểm tra dữ liệu bẩn)                 if qty < 0: 
                    raise ValueError(f"Stock cannot be negative: {qty}") 
                 
                print(f"   > Updated SKU: {sku} | New Qty: {qty}")          
        # Nếu đọc xong xuôi không lỗi -> Move sang folder Processed         shutil.move(filepath, os.path.join(PROCESSED_DIR, filename))         print(f"✅ Success! Moved to {PROCESSED_DIR}") 
     except Exception as e: 
        print(f"❌ Error processing file: {e}")         # Nếu lỗi -> Move sang folder Error 
        shutil.move(filepath, os.path.join(ERROR_DIR, filename))         print(f"⚠️ Moved to {ERROR_DIR}") 
 def start_watching(): 
    print("👀 Watchdog Service Started... Waiting for files in /input")     while True: 
        # 1. Quét tất cả file trong thư mục Input         files = os.listdir(INPUT_DIR) 
                 if files:             for file in files:                 if file.endswith('.csv'): 
                    # 2. Tạo đường dẫn đầy đủ và xử lý                     full_path = os.path.join(INPUT_DIR, file)                     process_file(full_path) 
         
        # 3. Ngủ 5 giây rồi quét tiếp (Cơ chế Polling)         time.sleep(5) 
 if __name__ == "__main__": 
    start_watching() 
 
 Giải thích cơ chế: 
•	time.sleep(5): Đây là nhịp tim của hệ thống. Nếu không có lệnh này, CPU sẽ bị quá tải vì vòng lặp while True chạy quá nhanh. 
•	shutil.move: Đây là hành động quan trọng nhất. Một file chỉ được xử lý đúng một lần. 
Sau khi xong, nó phải biến mất khỏi input để tránh vòng lặp vô tận. 
TASK 3: ĐÓNG GÓI VỚI DOCKER (VOLUME MAPPING) 
Mục đích: Giả lập môi trường thực tế nơi Container (Service) phải đọc file từ Máy chủ (Host). 
Bước 3.1: Tạo Dockerfile: 
Dockerfile 
 
FROM python:3.9-slim 
WORKDIR /app COPY watcher.py . 
CMD ["python", "watcher.py"] 
 
Bước 3.2: Build Image 
Bash 
docker build -t lab3-watcher . 
 
Bước 3.3: Run Container với Volume Mapping (Quan trọng!) 
Lệnh này sẽ nối thư mục input trên máy thật vào trong container. 
Bash 
 
docker run -d --name legacy_worker \   -v ${PWD}/input:/app/input \ 
  -v ${PWD}/processed:/app/processed \   -v ${PWD}/error:/app/error \   lab3-watcher 
 
(Nếu dùng Windows CMD, thay ${PWD} bằng đường dẫn tuyệt đối, ví dụ D:\Lab3_FileTransfer). 
Bước 3.4: Kiểm tra log để xem nó đang chạy: 
Bash 
 
docker logs -f legacy_worker 
 
Kết quả: Sẽ thấy dòng chữ  Watchdog Service Started.... Nó đang chờ đợi. 
 
TASK 4: KIỂM THỬ (THE MAGIC MOMENT) 
Mục đích: Xem hệ thống phản ứng thế nào khi có file rơi vào. 
Bước 4.1: Copy file data_2024.csv (đã tạo ở Task 1) và Paste vào thư mục input. 
Bước 4.2: Quan sát Terminal (cửa sổ log của Task 3.4). 
•	Bạn sẽ thấy Service phát hiện ra file. 
•	Nó đọc từng dòng. 
•	Đến dòng FRIDGE-LG, nó sẽ báo lỗi ValueError: Stock cannot be negative. 
•	Cuối cùng, nó chuyển file vào thư mục error. 
Bước 4.3: Kiểm tra trên máy thật. 
•	Vào thư mục input: File đã biến mất. • 	Vào thư mục error: File data_2024.csv nằm ở đây. 
•	-> Hệ thống hoạt động đúng thiết kế! 
E. THỬ THÁCH NÂNG CAO (CHALLENGE - 20% ĐIỂM) 
Vấn đề: Hiện tại, nếu file CSV có 1 dòng lỗi, toàn bộ file bị vứt vào thư mục Error. Các dòng đúng (như TV-SONY) cũng không được cập nhật. Điều này gây lãng phí. 
Yêu cầu: Hãy sửa hàm process_file để đạt được logic "Resilience" (Khả năng chịu lỗi): 1. Sử dụng try-catch cho từng dòng (bên trong vòng lặp for row in reader). 
2.	Nếu dòng nào lỗi -> Ghi log "Skipped bad row" và tiếp tục dòng sau. 
3.	Nếu dòng nào đúng -> In ra "Updated". 
4.	Cuối cùng, luôn di chuyển file vào processed (vì chúng ta đã xử lý xong hết mức có thể). 
Gợi ý: Di chuyển khối try-except vào trong vòng lặp for. 
 
F. HƯỚNG DẪN NỘP BÀI (SUBMISSION) 
Sinh viên nộp file nén [MSSV]_Lab3.zip gồm: 
1.	Báo cáo PDF: 
o	Ảnh chụp Terminal khi Container phát hiện file và xử lý. 
o	Ảnh chụp thư mục trên Windows cho thấy file đã bị di chuyển từ input sang processed (hoặc error). 
o	Giải thích cơ chế: Tại sao cần time.sleep(5)? 
2.	Source Code: watcher.py (phiên bản đã nâng cấp phần Challenge), Dockerfile 

LAB 4: DIRECT INTEGRATION - BUILDING REST API 
& SERVICE DISCOVERY 
A. THÔNG TIN CHUNG (META INFO) 
•	Môn học: CMU-CS 445 System Integration Practices. 
•	Ánh xạ kiến thức: Lecture 5 (Services & SOA) - RESTful Architecture & RPC. 
•	Thời lượng ước tính: 90 phút. 
•	Cấp độ: Trung bình (Intermediate). 
 
B. MỤC TIÊU & BỐI CẢNH (OBJECTIVES & SCENARIO) 
1. Kịch bản (Scenario) 
Trong Lab 3, chúng ta đã tích hợp qua File (chậm, độ trễ cao). Nhưng khi khách hàng đặt hàng Online, họ cần phản hồi tức thì ("Đặt hàng thành công!"). Chúng ta không thể bắt khách chờ 5 phút để quét file được. 
Nhiệm vụ của bạn là xây dựng cơ chế Direct Connection (Kết nối trực tiếp): 
1.	Service A (Order Service): Cung cấp một "cánh cửa" (API Endpoint) để nhận đơn hàng. 
2.	Service B (Client App): Gọi điện trực tiếp cho Service A để gửi đơn hàng. 
3.	Thách thức: Khi chạy trong Docker, làm sao Service B tìm thấy Service A? (Vấn đề Service Discovery). 
2. Mục tiêu kỹ thuật 
•	Hiểu cơ chế Request/Response (Synchronous). 
•	Xây dựng REST API với Python Flask (GET, POST). 
•	Cấu hình Docker Compose để nối mạng cho 2 containers. 
•	Hiểu khái niệm Internal DNS trong Docker. 
3. Sơ đồ kiến trúc (Architecture) 
 
C. CHUẨN BỊ (PREREQUISITES) 
1.	Phần mềm: Docker Desktop, VS Code, Postman (Bắt buộc để test API). 
2.	Tài nguyên: Tạo thư mục Lab4_API trên máy tính. 
 
D. CÁC BƯỚC THỰC HIỆN (STEP-BY-STEP) 
TASK 1: XÂY DỰNG SERVER (ORDER SERVICE) 
Mục đích: Tạo ra bên cung cấp dịch vụ (Provider). 
Bước 1.1: Trong Lab4_API, tạo thư mục con server. 
Bước 1.2: Tạo file server/app.py: 
Python 
 
from flask import Flask, request, jsonify 
 
app = Flask(__name__) 
 
# Giả lập Database trong bộ nhớ (In-memory DB) orders = [] 
 
@app.route('/orders', methods=['POST']) def create_order(): 
    # 1. Nhận dữ liệu JSON từ Client gửi lên     data = request.get_json() 
     
    # 2. Validate đơn giản     if not data or 'product' not in data or 'amount' not in data: 
        return jsonify({"error": "Invalid Data"}), 400 
     
    # 3. Lưu vào "Database"     new_order = { 
        "id": len(orders) + 1, 
        "product": data['product'], 
        "amount": data['amount'], 
        "status": "CONFIRMED" 
    } 
    orders.append(new_order) 
     
    print(f"Received Order: {new_order}")     return jsonify(new_order), 201 
 
@app.route('/orders', methods=['GET']) def get_orders(): 
    return jsonify({"total": len(orders), "data": orders}) 
 if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=5000) 
 
Bước 1.3: Tạo server/Dockerfile: 
Dockerfile 
 
FROM python:3.9-slim WORKDIR /app 
RUN pip install flask 
COPY . . 
CMD ["python", "app.py"] 
 
 
TASK 2: XÂY DỰNG CLIENT (TEST SCRIPT) 
Mục đích: Tạo ra bên sử dụng dịch vụ (Consumer). Đây là phần tích hợp. 
Bước 2.1: Tạo thư mục con client (ngang hàng với server). 
Bước 2.2: Tạo file client/test_api.py. 
Lưu ý quan trọng: Trong code dưới đây, URL không phải là localhost mà là http://my_order_service:5000. Đây là tên Service chúng ta sẽ đặt trong Docker Compose. Python 
 
import requests import time import sys 
 
# URL của Server trong mạng Docker 
# "my_order_service" là tên container server (Domain Name) 
API_URL = "http://my_order_service:5000/orders" 
 def simulate_user(): 
    print("Client started... Waiting for Server...")     time.sleep(5) # Chờ Server khởi động xong 
 
    # 1. Tạo đơn hàng giả lập 
    payload = {"product": "Laptop Dell", "amount": 1500} 
         try: 
        print(f"Sending request to: {API_URL}") 
        response = requests.post(API_URL, json=payload) 
                 if response.status_code == 201: 
            print(f" Success! Server replied: {response.json()}")         else:             print(f"❌ Failed: {response.text}") 
                 except Exception as e: 
        print(f"Connection Error: {e}") 
        print("Tip: Check if Server container is running and hostname is correct.") 
 if __name__ == "__main__": 
    simulate_user() 
 
Bước 2.3: Tạo client/Dockerfile: 
Dockerfile 
 
FROM python:3.9-slim 
WORKDIR /app 
RUN pip install requests COPY . . 
CMD ["python", "test_api.py"] 
 
🟢 TASK 3: KẾT NỐI BẰNG DOCKER COMPOSE (THE GLUE) 
Mục đích: Bật cả 2 container cùng lúc và cho chúng nhìn thấy nhau. 
Bước 3.1: Tại thư mục gốc Lab4_API, tạo file docker-compose.yml. 
YAML 
 
version: '3.8' 
 services: 
  # Service 1: Server 
  my_order_service:       # <-- Đây chính là tên miền (DNS Name)     build: ./server     ports: 
-	"8080:5000"       # Map cổng 5000 của container ra 8080 của máy thật 
 
  # Service 2: Client   my_client: 
    build: ./client     depends_on: 
-	my_order_service  # Client sẽ chờ Server chạy trước     environment: 
-	API_ENDPOINT=http://my_order_service:5000 
 
TASK 4: CHẠY VÀ KIỂM TRA 
Mục đích: Xem Client và Server "nói chuyện" với nhau. 
Bước 4.1: Mở Terminal tại thư mục gốc, chạy lệnh: 
Bash 
docker-compose up --build 
Bước 4.2: Quan sát Log trên màn hình. 
•	Bạn sẽ thấy log của Server: Running on http://0.0.0.0:5000. 
•	Bạn sẽ thấy log của Client: 📤 Sending request... sau đó là ✅ Success! Server replied.... 
Bước 4.3: Kiểm tra từ bên ngoài (Máy thật). 
•	Mở Postman. 
•	Gửi Request GET http://localhost:8080/orders. 
•	Kết quả: Bạn sẽ thấy đơn hàng "Laptop Dell" mà Client vừa tạo nằm trong danh sách. 
Giải thích cơ chế: 
•	localhost:8080: Là cổng dành cho BẠN (người dùng bên ngoài). • my_order_service:5000: Là cổng dành cho CLIENT (container bên trong). 
•	Đây là sự khác biệt giữa External Access và Internal Communication. 
 
E. THỬ THÁCH NÂNG CAO (CHALLENGE - 20% ĐIỂM) 
Vấn đề: Hiện tại Client gửi request xong là tắt. Server lưu dữ liệu vào RAM, nếu restart container là mất hết dữ liệu. 
Yêu cầu: 
1. Sửa docker-compose.yml: Thêm một Volume cho my_order_service. 
o	Map thư mục ./data ở máy thật vào /app/data trong container. 2. Sửa code server/app.py: 
o	Thay vì lưu vào biến orders = [], hãy ghi đơn hàng vào file JSON nằm trong /app/data/orders.json. 
o	Khi khởi động, đọc file này lên để khôi phục dữ liệu cũ. 
3. Kết quả: Sau khi tắt Docker (docker-compose down) và bật lại, đơn hàng cũ vẫn còn nguyên. 
 
F. HƯỚNG DẪN NỘP BÀI (SUBMISSION) 
Sinh viên nộp file nén [MSSV]_Lab4.zip gồm: 
1.	Báo cáo PDF: 
o	Ảnh chụp Terminal khi chạy docker-compose up (thấy Client gửi thành công). o 	Ảnh chụp Postman gọi GET /orders thấy dữ liệu. 
o	Giải thích: Tại sao trong code Client dùng http://my_order_service mà không dùng localhost? 
2.	Source Code: Folder server, client và file docker-compose.yml. 
 
LAB 5: ASYNCHRONOUS INTEGRATION - MESSAGE 
QUEUES WITH RABBITMQ 
A. THÔNG TIN CHUNG (META INFO) 
•	Môn học: CMU-CS 445 System Integration Practices. 
•	Ánh xạ kiến thức: Lecture 7 (Middleware) & Lecture 12 (Messaging Systems). 
•	Thời lượng ước tính: 90 - 100 phút. 
•	Cấp độ: Nâng cao (Advanced). 
 
B. MỤC TIÊU & BỐI CẢNH (OBJECTIVES & SCENARIO) 
1. Kịch bản (Scenario) 
Vào ngày Black Friday, Web Store của NOAH Retail nhận được 1,000 đơn hàng mỗi phút. Tuy nhiên, Hệ thống Kế toán (Finance) là phần mềm cũ, mất tới 5 giây để xử lý xong một hóa đơn. 
Nếu dùng cách gọi trực tiếp (như Lab 4), Web Store sẽ bị treo cứng vì phải chờ Kế toán. Khách hàng sẽ bỏ đi. 
Giải pháp: Sử dụng mô hình "Fire and Forget" (Bắn và Quên). Web Store ném đơn hàng vào một "Hộp thư" (Queue) rồi báo thành công ngay cho khách. Kế toán sẽ túc tắc lấy thư từ hộp ra xử lý dần dần. 
2.	Mục tiêu kỹ thuật • 	Hiểu mô hình Producer - Broker - Consumer. 
•	Cài đặt và cấu hình RabbitMQ bằng Docker. 
•	Viết code Python sử dụng thư viện pika để gửi/nhận tin nhắn. 
•	Hiểu cơ chế Message Acknowledgment (Đảm bảo không mất tin). 
3.	Sơ đồ kiến trúc (Architecture) 
 
C. CHUẨN BỊ (PREREQUISITES) 
1.	Phần mềm: Docker Desktop, VS Code. 
2.	Tài nguyên: Tạo thư mục Lab5_Messaging. 
3.	Thư viện: Chúng ta sẽ cài pika trong Docker. 
 
D. CÁC BƯỚC THỰC HIỆN (STEP-BY-STEP) 
TASK 1: KHỞI TẠO RABBITMQ BROKER 
Mục đích: Dựng "Bưu điện trung tâm" để chuyển phát tin nhắn. 
Bước 1.1: Tạo file docker-compose.yml tại thư mục gốc Lab5_Messaging. 
YAML 
 
version: '3.8' 
 services: 
  # Đây là Message Broker (Người trung gian)   my_rabbitmq: 
    image: rabbitmq:3-management     ports: 
      - "5672:5672"   # Cổng để App gửi tin nhắn       - "15672:15672" # Cổng để vào trang quản trị Web     environment: 
      RABBITMQ_DEFAULT_USER: user 
      RABBITMQ_DEFAULT_PASS: password 
 
Bước 1.2: Chạy lệnh: docker-compose up -d. 
Bước 1.3: Kiểm tra (Verify): 
•	Mở trình duyệt: http://localhost:15672. 
•	Đăng nhập: user / password. 
•	Nếu vào được giao diện màu cam của RabbitMQ là thành công. 
 
 TASK 2: VIẾT PRODUCER (NGƯỜI GỬI) 
Mục đích: Giả lập Web Store gửi đơn hàng. 
Bước 2.1: Tạo thư mục producer. Bên trong tạo file send.py. 
Python 
import pika import time import json import random 
 
# Cấu hình kết nối đến RabbitMQ 
# Lưu ý: 'my_rabbitmq' là tên service trong docker-compose credentials = pika.PlainCredentials('user', 'password') parameters = pika.ConnectionParameters('my_rabbitmq', 5672, '/', credentials) 
 def send_orders(): 
    # Chờ RabbitMQ khởi động 
    time.sleep(10)  
         try: 
        connection = pika.BlockingConnection(parameters)         channel = connection.channel() 
 
        # 1. Tạo hàng đợi tên là 'order_queue'         channel.queue_declare(queue='order_queue') 
 
        # 2. Gửi 10 đơn hàng liên tục         for i in range(1, 11): 
            order = { 
                "id": i, 
                "customer": f"User_{i}", 
                "amount": random.randint(100, 500) 
            } 
            message = json.dumps(order) 
             
            # Gửi tin nhắn 
            channel.basic_publish(exchange='', routing_key='order_queue', body=message)             print(f" [x] Sent Order #{i}") 
            time.sleep(1) # Giả lập khách đặt hàng mỗi giây 
         connection.close()     except Exception as e:         print(f"Error: {e}") 
 if __name__ == "__main__": 
    send_orders() 
 
Bước 2.2: Tạo producer/Dockerfile: 
Dockerfile 
 
FROM python:3.9-slim 
RUN pip install pika 
WORKDIR /app COPY send.py . 
CMD ["python", "send.py"] 
 
TASK 3: VIẾT CONSUMER (NGƯỜI NHẬN) 
Mục đích: Giả lập Hệ thống Kế toán xử lý chậm chạp. 
Bước 3.1: Tạo thư mục consumer. Bên trong tạo file receive.py. 
Python 
 
import pika import time import sys 
 
credentials = pika.PlainCredentials('user', 'password') parameters = pika.ConnectionParameters('my_rabbitmq', 5672, '/', credentials) 
 def callback(ch, method, properties, body):     print(f" [x] Received {body.decode()}")      
    # GIẢ LẬP XỬ LÝ CHẬM (Kế toán làm việc)     time.sleep(2)  
     
    print(" [x] Order Processed (Saved to DB)") 
     
    # Quan trọng: Báo cho RabbitMQ biết đã làm xong 
    # (Manual Acknowledgment) 
    ch.basic_ack(delivery_tag=method.delivery_tag) 
 def start_consuming(): 
    time.sleep(10) # Chờ RabbitMQ 
     
    connection = pika.BlockingConnection(parameters)     channel = connection.channel() 
 
    channel.queue_declare(queue='order_queue') 
 
    # Chỉ nhận 1 tin nhắn tại một thời điểm (Fair Dispatch)     channel.basic_qos(prefetch_count=1) 
     
    channel.basic_consume(queue='order_queue', on_message_callback=callback) 
 
    print(' [*] Waiting for orders. To exit press CTRL+C')     channel.start_consuming() 
 if __name__ == "__main__": 
    start_consuming() 
 
Bước 3.2: Tạo consumer/Dockerfile: 
Dockerfile 
 
FROM python:3.9-slim 
RUN pip install pika 
WORKDIR /app COPY receive.py . 
CMD ["python", "receive.py"] 
 
 
TASK 4: TÍCH HỢP VÀ CHẠY THỬ 
Mục đích: Chứng kiến sự "bất đồng bộ". 
Bước 4.1: Cập nhật docker-compose.yml, thêm 2 service mới: 
YAML 
 
version: '3.8' services:   my_rabbitmq: 
    # ... (giữ nguyên như Task 1) ... 
   producer: 
    build: ./producer 
    depends_on: [my_rabbitmq] 
   consumer: 
    build: ./consumer     depends_on: [my_rabbitmq] 
 
Bước 4.2: Chạy lại toàn bộ: 
Bash 
 
docker-compose up –build 
 
Bước 4.3: Quan sát Terminal. 
•	Producer: Bạn sẽ thấy nó bắn tin rất nhanh: Sent Order #1, Sent Order #2, Sent Order #3... (Mỗi giây 1 đơn). 
•	Consumer: Bạn sẽ thấy nó xử lý rất từ tốn: Received... -> (Đợi 2 giây) -> Processed. • 	Hiện tượng: Dù Consumer xử lý chậm, Producer không bị chặn. Các đơn hàng chưa xử lý sẽ nằm xếp hàng trong RabbitMQ. 
 
E. THỬ THÁCH NÂNG CAO (CHALLENGE - QUAN TRỌNG) 
Vấn đề: Điều gì xảy ra nếu RabbitMQ bị sập (Crash) khi tin nhắn đang nằm trong hàng đợi? Mặc định, tin nhắn nằm trong RAM nên sẽ mất sạch. 
Yêu cầu: Hãy làm cho tin nhắn trở nên Bền vững (Durable) - Không mất dù RabbitMQ khởi động lại. 1. Sửa code send.py và receive.py: 
	o 	Trong hàm queue_declare, thêm tham số durable=True. 
2.	Sửa code send.py (phần basic_publish): 
	o 	Thêm properties=pika.BasicProperties(delivery_mode=2). (Mode 2 = 
Persistent). 
3.	Test: Chạy Producer gửi 10 tin. Tắt Consumer đi. Sau đó Restart RabbitMQ container. Bật Consumer lại. Tin nhắn phải vẫn còn và được xử lý tiếp. 
 
F. HƯỚNG DẪN NỘP BÀI (SUBMISSION) 
Sinh viên nộp file nén [MSSV]_Lab5.zip gồm: 
1.	Báo cáo PDF: 
o 	Ảnh chụp giao diện Web RabbitMQ (http://localhost:15672) hiển thị biểu đồ Queue. o 	Ảnh chụp Terminal thể hiện Producer gửi nhanh còn Consumer xử lý chậm. o 	Giải thích ý nghĩa lệnh ch.basic_ack (Tại sao cần báo nhận?). 
2.	Source Code: Folder producer, consumer, docker-compose.yml. 
• 	Chú ý lỗi phổ biến: Sinh viên hay quên khai báo my_rabbitmq trong code Python, dẫn đến lỗi kết nối. 
 
 LAB 6: SECURITY & GOVERNANCE - API GATEWAY WITH KONG 
A. THÔNG TIN CHUNG (META INFO) 
•	Môn học: CMU-CS 445 System Integration Practices. 
•	Ánh xạ kiến thức: Lecture 10 (System Management & Security) - API Gateway Pattern. 
•	Thời lượng ước tính: 90 phút. 
•	Cấp độ: Nâng cao (Advanced). 
 
B. MỤC TIÊU & BỐI CẢNH (OBJECTIVES & SCENARIO) 
1. Kịch bản (Scenario) 
Ở Lab 4, chúng ta đã mở toang cánh cửa cho Client gọi vào Order Service. Điều này rất nguy hiểm: 
1.	Bất kỳ ai cũng có thể spam tạo đơn hàng rác (DDoS). 
2.	Không ai kiểm soát xem người gọi là ai (Authentication). 
Nhiệm vụ của bạn là thuê một "Bảo vệ" (Bouncer) đứng trước cửa. Tên anh ta là Kong Gateway. 
•	Khách muốn vào phải đi qua Kong (Cổng 8000). 
•	Phải trình thẻ ra vào (API Key). 
•	Nếu không có thẻ -> Kong đá ra ngoài (401 Unauthorized). 
•	Service bên trong (backend) sẽ ẩn mình, không tiếp khách trực tiếp nữa. 
2. Mục tiêu kỹ thuật 
•	Hiểu mô hình Reverse Proxy. 
•	Cấu hình Kong Gateway ở chế độ DB-less (Dùng file YAML, không cần Database, dễ triển khai). 
•	Cài đặt Plugin Key Authentication để bảo mật API. 
•	Cài đặt Plugin Rate Limiting để chống spam (Phần Challenge). 
3. Sơ đồ kiến trúc (Architecture) 
 
C. CHUẨN BỊ (PREREQUISITES) 
1.	Phần mềm: Docker Desktop, VS Code, Postman (Bắt buộc). 
2.	Tài nguyên: Tạo thư mục Lab6_Gateway. 
 
D. CÁC BƯỚC THỰC HIỆN (STEP-BY-STEP) 
🟢 TASK 1: CHUẨN BỊ BACKEND (MỤC TIÊU CẦN BẢO VỆ) 
Mục đích: Dựng lại cái API đơn giản của Lab 4 để làm chuột bạch. 
Bước 1.1: Trong Lab6_Gateway, tạo thư mục backend. 
Bước 1.2: Tạo file backend/app.py (Code Flask siêu đơn giản): 
Python 
 
from flask import Flask, jsonify app = Flask(__name__) 
 
@app.route('/api/private', methods=['GET']) def secret_data():     return jsonify({ 
        "status": "success", 
        "message": "Welcome VIP! You have accessed the protected area.", 
        "secret_code": 123456 
    }), 200 
 if __name__ == '__main__': 
    app.run(host='0.0.0.0', port=5000) 
 
Bước 1.3: Tạo backend/Dockerfile: 
Dockerfile 
 
FROM python:3.9-slim 
RUN pip install flask 
WORKDIR /app COPY app.py . 
CMD ["python", "app.py"] 
 
🟢 TASK 2: CẤU HÌNH KONG (DB-LESS MODE) 
Mục đích: Viết luật cho bảo vệ (File cấu hình YAML). 
Bước 2.1: Tại thư mục gốc Lab6_Gateway, tạo file kong.yml. 
Đây là file "bản đồ" chỉ đường cho Kong: 
YAML 
 
_format_version: "2.1" 
_transform: true 
 
# 1. Định nghĩa Service (Backend nằm ở đâu?) services: 
-	name: my-secret-service 
    url: http://backend_container:5000  # Tên container trong Docker Compose 
    # 2. Định nghĩa Route (Đường dẫn nào sẽ dẫn vào Service này?)     routes: 
-	name: my-secret-route         paths: 
-	/secure-api  # Khi user gọi http://kong:8000/secure-api 
                         # Kong sẽ chuyển tiếp vào http://backend:5000/api/private 
    # 3. Kích hoạt Plugin bảo mật cho Service này     plugins: 
-	name: key-auth   # Bắt buộc phải có API Key 
 
# 4. Định nghĩa Khách hàng (Consumers) và Key consumers: 
-	username: student_admin     keyauth_credentials: 
-	key: noah-secret-key-2024 
 
 Giải thích: 
•	url: Chúng ta dùng tên container backend_container vì Kong và Backend sẽ nằm chung mạng Docker. 
•	paths: Đường dẫn ảo. Người dùng gọi /secure-api, Kong sẽ dịch sang đường dẫn thật của Backend. • plugins: Lệnh kích hoạt ổ khóa key-auth. 
 
 TASK 3: KẾT NỐI HẠ TẦNG (DOCKER COMPOSE) 
Mục đích: Bật Backend và Kong lên cùng lúc. 
Bước 3.1: Tạo file docker-compose.yml tại thư mục gốc. 
YAML 
version: '3.8' 
 services: 
  # 1. Backend Service (Mục tiêu cần bảo vệ)   backend_container:     build: ./backend 
    # Lưu ý: KHÔNG expose cổng 5000 ra máy thật (ports).     # Chỉ Kong mới nhìn thấy Backend này. (Isolation)  
  # 2. Kong Gateway (Người bảo vệ)   kong: 
    image: kong:2.8     volumes: 
-	./kong.yml:/usr/local/kong/declarative/kong.yml # Nạp file cấu hình vào     environment: 
-	KONG_DATABASE=off                            # Chế độ không DB 
-	KONG_DECLARATIVE_CONFIG=/usr/local/kong/declarative/kong.yml 
-	KONG_PROXY_ACCESS_LOG=/dev/stdout 
-	KONG_ADMIN_ACCESS_LOG=/dev/stdout 
-	KONG_PROXY_ERROR_LOG=/dev/stderr 
-	KONG_ADMIN_ERROR_LOG=/dev/stderr 
-	KONG_ADMIN_LISTEN=0.0.0.0:8001, 0.0.0.0:8444 ssl     ports: 
-	"8000:8000"  # Cổng chính để Client gọi vào 
-	"8001:8001"  # Cổng Admin (quản trị) 
 
 TASK 4: CHẠY VÀ KIỂM THỬ (VERIFICATION) 
Mục đích: Đóng vai Hacker và User hợp lệ. 
Bước 4.1: Chạy hệ thống: 
Bash 
docker-compose up --build 
Bước 4.2: Test 1 - Truy cập không có chìa khóa (Hacker). 
•	Mở Postman (hoặc trình duyệt). 
•	Gửi GET request: http://localhost:8000/secure-api/api/private o 	Lưu ý: Vì cấu hình path trong kong.yml hơi phức tạp, để đơn giản, Kong sẽ nối đuôi path. Cụ thể: Nó map /secure-api vào url. Nên URL đầy đủ là localhost:8000/secure-api + /api/private (của flask). 
	o 	Sửa lại Route trong Bước 2.1 cho dễ hiểu: 
Nếu config: paths: ["/"] cho đơn giản thì gọi localhost:8000/api/private. 
Nhưng hãy giữ nguyên cấu hình trên và gọi: http://localhost:8000/secure-api/api/private 
•	Kết quả: 401 Unauthorized 
JSON 
{ "message": "No API key found in request" } 
•	-> Bảo vệ đã chặn thành công! 
Bước 4.3: Test 2 - Truy cập có chìa khóa (VIP User). 
•	Trong Postman, thêm Header: 
o 	Key: apikey o 	Value: noah-secret-key-2024 
•	Gửi lại Request. • 	Kết quả: 200 OK -> Thấy được "secret_code". 
 
E. THỬ THÁCH NÂNG CAO (CHALLENGE - 20% ĐIỂM) 
Vấn đề: Mặc dù đã có Key, nhưng nếu một user hợp lệ cố tình spam 1 triệu request/giây thì backend vẫn sập. 
Nhiệm vụ: Cấu hình Rate Limiting (Giới hạn tốc độ). 
1.	Mở file kong.yml. 
2.	Thêm plugin rate-limiting vào danh sách plugins: 
YAML 
plugins:   - name: key-auth   - name: rate-limiting     config: 
      minute: 5  # Chỉ cho phép 5 request mỗi phút       policy: local 
3.	Restart container Kong (docker-compose restart kong). 
4.	Test: Vào Postman, bấm nút Send liên tục 6 lần. 5. Kết quả: Lần thứ 6 phải nhận được lỗi 429 Too Many Requests. 
 
F. HƯỚNG DẪN NỘP BÀI (SUBMISSION) 
Sinh viên nộp file nén [MSSV]_Lab6.zip gồm: 
1.	Báo cáo PDF: 
o	Ảnh chụp Postman khi bị chặn (401 Unauthorized). 
o	Ảnh chụp Postman khi thành công (200 OK). 
o	Ảnh chụp Postman khi bị Rate Limit (429 Too Many Requests). 
2.	Source Code: Folder backend, file kong.yml, docker-compose.yml. 
•	Bài Lab này có thể hơi khó ở phần Path Matching (Đường dẫn ảo vs Đường dẫn thật). Thầy/Cô nên nhắc sinh viên: "Kong nối cái đuôi path của bạn vào sau cái url gốc của service". 
•	Đây là bước đệm để Module 4 của Đồ án (Cấu hình Kong cho Dashboard và Order API) trở nên dễ dàng. 
 
