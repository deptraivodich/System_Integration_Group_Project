# HƯỚNG DẪN CHẠY DỰ ÁN: NOAH RETAIL UNIFIED COMMERCE
> **Tài liệu này dành cho tất cả thành viên nhóm.**  
> Mỗi khi hoàn thành một module, **cập nhật trạng thái vào bảng tiến độ** và push lên GitHub.

---

## ✅ CHECKLIST TRƯỚC KHI BẮT ĐẦU

| Yêu cầu | Kiểm tra |
|---------|---------|
| Docker Desktop đang chạy | `docker --version` |
| Docker Compose | `docker compose version` |
| Python 3.9+ (để chạy tests local) | `python --version` |
| Port trống: 3306, 5432, 5672, 15672, 5000 | Không có app nào chiếm |

---

## PHẦN 1: CHẠY TOÀN BỘ HỆ THỐNG

### Bước 1: Clone và vào thư mục
```bash
git clone <repo-url>
cd System_Integration_Group_Project
```

### Bước 2: Khởi động toàn bộ (lần đầu — có build)
```bash
docker compose up -d --build
```
> ⏳ Lần đầu mất **3–5 phút** do phải build images và pull MySQL/PostgreSQL/RabbitMQ.

### Bước 3: Kiểm tra tất cả services đang chạy
```bash
docker compose ps
```
**Kết quả mong đợi:**
```
NAME                STATUS          PORTS
noah_mysql          Up (healthy)    0.0.0.0:3306->3306/tcp
noah_postgres       Up (healthy)    0.0.0.0:5432->5432/tcp
noah_rabbitmq       Up (healthy)    0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
noah_module1        Up              
noah_order_api      Up (healthy)    0.0.0.0:5000->5000/tcp
noah_order_worker   Up              
```

### Bước 4: Test nhanh pipeline
```bash
# 1. Gửi đơn hàng thử
curl -X POST http://localhost:5000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product_id": 101, "quantity": 2}'

# Kết quả mong đợi:
# {"message": "Order received", "order_id": 1, "status": "PENDING"}

# 2. Chờ 3-4 giây, kiểm tra trạng thái
curl http://localhost:5000/api/orders/1

# Kết quả mong đợi: "status": "COMPLETED"
```

### Bước 5: Dừng hệ thống
```bash
docker compose down        # Dừng nhưng GIỮ data (volumes)
docker compose down -v     # Dừng và XÓA SẠCH data (reset hoàn toàn)
```

---

## PHẦN 2: CHẠY TỪNG MODULE ĐỘC LẬP

> **Quan trọng:** Các module phụ thuộc vào nhau. Thứ tự khởi động đúng:  
> `MySQL + PostgreSQL + RabbitMQ` → `Module 1` → `Module 2A` → `Module 2B`

---

### MODULE 0: Hạ Tầng (Infrastructure chỉ)
```bash
# Chỉ khởi động 3 database/broker (không có services Python)
docker compose up -d mysql_db postgres_db rabbitmq

# Kiểm tra healthy
docker compose ps mysql_db postgres_db rabbitmq
```

**Xác nhận MySQL:**
```bash
docker exec -it noah_mysql mysql -uroot -p123456 -e "SHOW DATABASES;"
# Phải thấy: noah_retail
```

**Xác nhận PostgreSQL:**
```bash
docker exec -it noah_postgres psql -U postgres -c "\l"
# Phải thấy: noah_finance
```

**Xác nhận RabbitMQ:**
- Mở trình duyệt: http://localhost:15672
- Đăng nhập: `user` / `password`
- Thấy giao diện dashboard màu cam = OK ✅

---

### MODULE 1: Legacy Adapter (CSV Watchdog)

**Yêu cầu trước:** Module 0 đang chạy (mysql_db healthy)

```bash
# Chỉ chạy module1
docker compose up -d module1_watcher

# Xem log realtime
docker logs -f noah_module1
```

**Test Module 1:**
```bash
# Tạo file CSV mẫu
cat > /tmp/inventory.csv << 'EOF'
product_id,quantity
100,50
101,30
102,-5
103,abc
104,20
EOF

# Copy vào volume input của container
docker cp /tmp/inventory.csv noah_module1:/app/input_data/inventory.csv
```
> **Trên Windows:** Dùng lệnh sau thay thế
```powershell
# Tạo CSV test
"product_id,quantity`n100,50`n101,30`n102,-5`n103,abc`n104,20" | Out-File -FilePath "$env:TEMP\inventory.csv" -Encoding UTF8
# Copy vào container
docker cp "$env:TEMP\inventory.csv" noah_module1:/app/input_data/inventory.csv
```

**Kết quả mong đợi trong log:**
```
[+] Đang xử lý file: inventory.csv
⚠️ Phát hiện 2 dòng lỗi. Đã lưu log tại: error_data/...
✅ Cập nhật dữ liệu vào DB thành công!
✅ Đã di chuyển file gốc RAW sang: processed_data/
```

**Kiểm tra MySQL:**
```bash
docker exec -it noah_mysql mysql -uroot -p123456 noah_retail \
  -e "SELECT id, stock FROM products WHERE id IN (100, 101, 104);"
```

---

### MODULE 2A: Order API (Producer)

**Yêu cầu trước:** `mysql_db` + `rabbitmq` đang chạy và healthy

```bash
# Chỉ chạy Order API
docker compose up -d order_api

# Kiểm tra health
curl http://localhost:5000/health
# → {"status": "ok", "service": "order_api"}
```

**Test gửi đơn hàng:**
```bash
# Đơn hàng hợp lệ → 202
curl -X POST http://localhost:5000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product_id": 101, "quantity": 5}'

# Đơn hàng không hợp lệ (quantity = 0) → 422
curl -X POST http://localhost:5000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product_id": 101, "quantity": 0}'
```

**Kiểm tra MySQL có đơn PENDING:**
```bash
docker exec -it noah_mysql mysql -uroot -p123456 noah_retail \
  -e "SELECT * FROM orders ORDER BY id DESC LIMIT 5;"
```

**Kiểm tra RabbitMQ có message trong queue:**
- Vào http://localhost:15672 → Queues → `order_queue`
- Thấy số `Ready` tăng = message đang chờ worker xử lý

**Xem log API:**
```bash
docker logs -f noah_order_api
```

---

### MODULE 2B: Order Worker (Consumer)

**Yêu cầu trước:** `mysql_db` + `postgres_db` + `rabbitmq` đang chạy

```bash
# Chỉ chạy Worker
docker compose up -d order_worker

# Xem log worker xử lý
docker logs -f noah_order_worker
```

**Kết quả mong đợi:**
```
[Worker] 🎧 Đang lắng nghe queue 'order_queue'...
[Worker] Nhận được order_id=1 | user_id=1 | product_id=101 | qty=5
[Worker] Đang xử lý thanh toán... (giả lập 1.5s)
[PostgreSQL] Đã INSERT transaction cho order_id=1
[MySQL] Đã UPDATE order_id=1 → COMPLETED
[Worker] ✅ Order #1 synced. ACK đã gửi.
```

**Kiểm tra PostgreSQL:**
```bash
docker exec -it noah_postgres psql -U postgres -d noah_finance \
  -c "SELECT * FROM transactions ORDER BY id DESC LIMIT 5;"
```

**Kiểm tra MySQL order đã COMPLETED:**
```bash
docker exec -it noah_mysql mysql -uroot -p123456 noah_retail \
  -e "SELECT id, status FROM orders ORDER BY id DESC LIMIT 5;"
```

---

### MODULE 3: Dashboard (TODO - cập nhật sau khi làm xong)

```bash
# Thành viên phụ trách Module 3 cập nhật phần này
# docker compose up -d report_service
# curl http://localhost:8080/api/report
```

---

### MODULE 4: Kong Gateway (TODO - cập nhật sau khi làm xong)

```bash
# Thành viên phụ trách Module 4 cập nhật phần này
# docker compose up -d kong
# curl -H "apikey: noah-secret-key" http://localhost:8000/api/orders
```

---

## PHẦN 3: CHẠY UNIT TESTS (Không cần Docker)

```bash
# Cài thư viện test (1 lần)
py -3.13 -m pip install fastapi uvicorn pika mysql-connector-python pydantic psycopg2-binary httpx pytest

# Chạy tất cả tests Module 2
py -3.13 -m pytest Module2/tests/ -v

# Kết quả mong đợi: 23 passed
```

---

## PHẦN 4: XEM LOG & DEBUG

```bash
# Xem log tất cả services cùng lúc
docker compose logs -f

# Xem log từng service
docker logs -f noah_mysql
docker logs -f noah_postgres
docker logs -f noah_rabbitmq
docker logs -f noah_module1
docker logs -f noah_order_api
docker logs -f noah_order_worker

# Vào bên trong container debug
docker exec -it noah_mysql bash
docker exec -it noah_postgres bash
docker exec -it noah_order_api bash
```

---

## PHẦN 5: PORTS MAPPING

| Service | Port ngoài (Host) | Port trong (Container) | Dùng để |
|---------|------------------|----------------------|---------|
| MySQL | 3306 | 3306 | Kết nối DB tool (Workbench, DBeaver) |
| PostgreSQL | 5432 | 5432 | Kết nối DB tool |
| RabbitMQ AMQP | 5672 | 5672 | App gửi/nhận message |
| RabbitMQ UI | 15672 | 15672 | http://localhost:15672 |
| Order API | 5000 | 5000 | http://localhost:5000 |
| Kong Gateway | 8000 | 8000 | (Module 4) |

---

## PHẦN 6: RESET & CLEAN

```bash
# Restart 1 service (khi sửa code)
docker compose up -d --build order_api

# Reset hoàn toàn (xóa data, build lại)
docker compose down -v
docker compose up -d --build

# Xóa tất cả images cũ (giải phóng disk)
docker system prune -a
```

---

## PHẦN 7: BẢNG TIẾN ĐỘ (CẬP NHẬT KHI XONG)

> **Thành viên:** Sau khi hoàn thành module của mình, cập nhật bảng này và push lên GitHub.

| Module | Người phụ trách | Trạng thái | Ngày hoàn thành | Ghi chú |
|--------|----------------|------------|----------------|---------|
| Module 0 - Hạ tầng | [Tên] | ✅ Done | 2026-04-25 | docker-compose.yml |
| Module 1 - CSV Watchdog | [Tên] | ✅ Done | 2026-04-25 | 5 lần retry |
| Module 2A - Order API | [Tên] | ✅ Done | 2026-04-25 | 13 tests |
| Module 2B - Order Worker | [Tên] | ✅ Done | 2026-04-25 | 10 tests |
| Module 3 - Dashboard | [Tên] | ❌ Todo | - | - |
| Module 4 - Kong Gateway | [Tên] | ❌ Todo | - | - |
