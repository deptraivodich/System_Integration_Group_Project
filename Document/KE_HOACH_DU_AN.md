# KẾ HOẠCH DỰ ÁN: NOAH RETAIL UNIFIED COMMERCE
> Môn: CMU-CS 445 System Integration Practices  
> Hình thức: Nhóm | Thời gian: 4 tuần

---

## 1. TỔNG QUAN KIẾN TRÚC

```
inventory.csv (Legacy)
        │  polling 5s
        ▼
  [Module 1]              [Module 2A]              [Module 2B]
  CSV Watchdog   ───────► Order API (FastAPI) ───► Order Worker
  (Python)       MySQL    (POST /api/orders)       (Consumer)
                  ▲        MySQL: PENDING            │
                  │        RabbitMQ: publish         │
                  │                                  ▼
                  │                          PostgreSQL (Finance)
                  │                          MySQL: COMPLETED
                  │
                  └──────────── [Module 3] Dashboard ──── [Module 4] Kong Gateway
                                (GET /api/report)          (API Key + Rate Limit)
```

**Stack hạ tầng:**
| Thành phần | Version | Chức năng |
|------------|---------|-----------|
| MySQL | 8.0 | Web Store Database |
| PostgreSQL | 15 | Finance Database |
| RabbitMQ | 3-management | Message Broker |
| Kong | 2.8 | API Gateway |
| Docker Compose | - | Orchestration |

---

## 2. KẾ HOẠCH TỪNG MODULE

---

### MODULE 0: HẠ TẦNG (Infrastructure)
**Mức độ:** Foundation | **Thời gian ước tính:** 2 giờ

| Hạng mục | Chi tiết |
|----------|----------|
| Nhiệm vụ | Dựng môi trường Docker toàn hệ thống |
| File chính | `docker-compose.yml` (root) |
| **Trạng thái** | ✅ **HOÀN THÀNH** |

**Checklist:**
- [x] MySQL 8.0 container + healthcheck
- [x] PostgreSQL 15 container + healthcheck
- [x] RabbitMQ 3-management container + healthcheck
- [x] Internal network `noah_network`
- [x] Volumes persist data
- [ ] Kong Gateway (thêm sau Module 4)

**File output:**
```
docker-compose.yml     ← root của project
```

---

### MODULE 1: LEGACY ADAPTER (CSV Watchdog)
**Mức độ:** Intermediate | **Thời gian ước tính:** 3 giờ  
**Lab tham khảo:** Lab 3 (File Transfer)

| Hạng mục | Chi tiết |
|----------|----------|
| Input | File `inventory.csv` trong `/app/input_data` |
| Output | MySQL `products.stock` cập nhật + file moved sang `/processed_data` |
| **Trạng thái** | ✅ **HOÀN THÀNH** |

**Checklist:**
- [x] Polling thư mục mỗi 5 giây
- [x] Validate: quantity < 0 → bỏ qua + log
- [x] Validate: thiếu dữ liệu / sai format → bỏ qua
- [x] UPDATE MySQL `products.stock`
- [x] Move file sang `processed_data/` sau khi xử lý
- [x] Ghi log lỗi sang `error_data/`
- [x] Retry connection (5 lần, delay 5s)
- [x] Dockerfile

**File output:**
```
Module1/
├── module1.py
├── Dockerfile
├── init.sql
├── input_data/
├── processed_data/
├── error_data/
└── cleaned_data/
```

**Test thủ công:**
```bash
# Copy CSV vào volume để test
docker cp test_inventory.csv noah_module1:/app/input_data/inventory.csv
# Xem log
docker logs -f noah_module1
```

---

### MODULE 2: ORDER PIPELINE (2A + 2B)
**Mức độ:** Advanced | **Thời gian ước tính:** 5 giờ  
**Lab tham khảo:** Lab 4 (REST API) + Lab 5 (RabbitMQ Messaging)

#### 2A: Order API (Producer)

| Hạng mục | Chi tiết |
|----------|----------|
| Endpoint | `POST /api/orders` |
| Input | `{"user_id": 1, "product_id": 101, "quantity": 2}` |
| Output | 202 Accepted + `{"message": "Order received", "order_id": 123}` |
| **Trạng thái** | ✅ **HOÀN THÀNH** |

**Checklist:**
- [x] FastAPI service, port 5000
- [x] Validate: quantity > 0; user_id, product_id > 0
- [x] INSERT MySQL `orders` với `status = PENDING`
- [x] Publish JSON vào RabbitMQ queue `order_queue` (durable, persistent)
- [x] Trả 202 ngay lập tức (không chờ worker)
- [x] GET `/api/orders/{id}` kiểm tra trạng thái
- [x] GET `/health` endpoint
- [x] Retry connection MySQL + RabbitMQ (10 lần)
- [x] Dockerfile

#### 2B: Order Worker (Consumer)

| Hạng mục | Chi tiết |
|----------|----------|
| Input | Message từ RabbitMQ `order_queue` |
| Output | PostgreSQL `transactions` insert + MySQL `orders.status = COMPLETED` |
| **Trạng thái** | ✅ **HOÀN THÀNH** |

**Checklist:**
- [x] Consume từ `order_queue` liên tục
- [x] Sleep 1–2s (giả lập payment processing)
- [x] INSERT vào PostgreSQL `transactions`
- [x] UPDATE MySQL `orders.status = COMPLETED`
- [x] Manual ACK (đảm bảo không mất message)
- [x] NACK + requeue khi lỗi xử lý
- [x] NACK + không requeue khi JSON lỗi
- [x] Queue `durable=True`, message `delivery_mode=2`
- [x] Retry connection tất cả services (10 lần)
- [x] Auto-create PostgreSQL table khi startup
- [x] Dockerfile

**Test:**
```bash
# Chạy unit tests (không cần Docker)
py -3.13 -m pytest Module2/tests/ -v
# → 23 passed
```

**File output:**
```
Module2/
├── order_api/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── order_worker/
│   ├── worker.py
│   ├── Dockerfile
│   └── requirements.txt
├── init_module2.sql
└── tests/
    ├── test_order_api.py   (13 tests)
    └── test_worker.py      (10 tests)
```

---

### MODULE 3: DASHBOARD (Report Service)
**Mức độ:** Advanced | **Thời gian ước tính:** 5 giờ  
**Lab tham khảo:** Lab 2 (ETL / Data Integration)

| Hạng mục | Chi tiết |
|----------|----------|
| Endpoint | `GET /api/report` |
| Input | MySQL (orders, products) + PostgreSQL (transactions) |
| Output | JSON tổng hợp + giao diện web Dashboard |
| **Trạng thái** | ❌ **CHƯA LÀM** |

**Checklist:**
- [ ] Service Python kết nối đồng thời MySQL + PostgreSQL
- [ ] Query đơn hàng từ MySQL (có phân trang LIMIT/OFFSET)
- [ ] Query transactions từ PostgreSQL
- [ ] Data Stitching: join 2 nguồn theo `order_id`
- [ ] Tính tổng doanh thu theo `user_id`
- [ ] `GET /api/report` trả JSON
- [ ] Giao diện web Dashboard (Streamlit hoặc HTML)
- [ ] Phân trang (pagination) cho list orders
- [ ] Dockerfile

**Schema output API:**
```json
{
  "total_orders": 150,
  "total_revenue": 5000000,
  "orders": [
    {
      "order_id": 1,
      "user_id": 1,
      "status": "COMPLETED",
      "transaction_status": "SYNCED"
    }
  ]
}
```

---

### MODULE 4: SECURITY (Kong Gateway)
**Mức độ:** Advanced | **Thời gian ước tính:** 3 giờ  
**Lab tham khảo:** Lab 6 (API Gateway)

| Hạng mục | Chi tiết |
|----------|----------|
| Input | Request từ client qua port 8000 |
| Output | Route đến đúng service + enforce security |
| **Trạng thái** | ❌ **CHƯA LÀM** |

**Checklist:**
- [ ] Kong DB-less mode (file `kong.yml`)
- [ ] Route `/orders` → `order_api:5000`
- [ ] Route `/report` → `report_service:8080`
- [ ] Plugin: `key-auth` (header `apikey: noah-secret-key`)
- [ ] Plugin: `rate-limiting` (10 req/phút/client)
- [ ] Order API không expose port 5000 ra ngoài (chỉ qua Kong)
- [ ] Cập nhật `docker-compose.yml` thêm Kong service

**Test:**
```bash
# Không có key → 401
curl http://localhost:8000/api/orders

# Có key → thành công
curl -H "apikey: noah-secret-key" http://localhost:8000/api/orders

# Spam 11 lần → lần 11 nhận 429
```

---

## 3. TIẾN ĐỘ TỔNG THỂ

```
Module 0 [##########] 100% ✅ Hạ tầng
Module 1 [##########] 100% ✅ CSV Watchdog
Module 2 [##########] 100% ✅ Order Pipeline (23/23 tests)
Module 3 [          ]   0% ❌ Dashboard
Module 4 [          ]   0% ❌ Kong Gateway
```

---

## 4. PHÂN CÔNG NHÓM (GỢI Ý)

| Thành viên | Module | Deadline |
|-----------|--------|----------|
| [Tên 1] | Module 0 + 1 | Tuần 1 |
| [Tên 2] | Module 2A + 2B | Tuần 2 |
| [Tên 3] | Module 3 Dashboard | Tuần 3 |
| [Tên 4] | Module 4 Kong + Testing | Tuần 3 |
| Cả nhóm | Integration Test + Report | Tuần 4 |

---

## 5. MA TRẬN ĐÁNH GIÁ

| Hạng mục | Trọng số | Trạng thái |
|----------|----------|------------|
| Logic tích hợp (dòng chảy data) | 3.0đ | ✅ Module 1+2 done |
| Hạ tầng DevOps (docker-compose) | 2.0đ | ✅ Done |
| Dashboard & UI/UX | 2.0đ | ❌ Module 3 |
| Sáng tạo & giá trị thêm | 2.0đ | ❌ Chọn option |
| Độ bền vững (retry, dirty data) | 1.0đ | ✅ Done |
| **TỔNG** | **10.0đ** | |
