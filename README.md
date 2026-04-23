# 📦 Inventory Data Processing - Module 1

## 📌 Giới thiệu

Dự án này thực hiện xử lý dữ liệu tồn kho từ file CSV bị lỗi (**Dirty Data - Missing Values**) và cập nhật vào hệ thống cơ sở dữ liệu MySQL.

Hệ thống bao gồm:

* Làm sạch dữ liệu CSV
* Tổng hợp tồn kho theo sản phẩm
* Cập nhật vào database
* Xuất dữ liệu đã xử lý ra file CSV mới

---

## 📁 Cấu trúc thư mục

```
project/
│
├── module1.py
├── init.sql
├── input_data/
│   └── inventory.csv
├── output_data/
│   └── inventory_cleaned.csv
```

---

## ⚙️ Yêu cầu hệ thống

* Python >= 3.8
* MySQL Server
* Thư viện Python:

```bash
pip install pandas mysql-connector-python
```

---

## 🚀 Hướng dẫn chạy dự án

### 🔥 Bước 1: Chuẩn bị dữ liệu

* Tạo thư mục:

```
input_data/
```

* Copy file CSV được cấp (`inventory.csv`) vào:

```
input_data/inventory.csv
```

---

### 🔥 Bước 2: Khởi tạo Database

Mở MySQL Workbench và chạy:

```sql
CREATE DATABASE inventory_management;
USE inventory_management;
```

Sau đó:

* Mở file `init.sql`
* Run toàn bộ script

👉 Kết quả:

* Tạo bảng `products`
* Có dữ liệu ban đầu

---

### 🔥 Bước 3: Cấu hình kết nối database

Mở file `module1.py`, chỉnh sửa:

```python
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123456",  # đổi theo máy bạn
    database="inventory_management"
)
```

---

### 🔥 Bước 4: Chạy chương trình

Trong terminal:

```bash
python module1.py
```

---

## 🔄 Luồng xử lý dữ liệu

```
inventory.csv (dirty data)
        ↓
Xử lý missing values (fill median)
        ↓
Group theo product_id
        ↓
Update vào MySQL (products.stock)
        ↓
Xuất file inventory_cleaned.csv
```

---

## 📊 Kết quả

Sau khi chạy thành công:

### ✅ Database

* Bảng `products.stock` được cập nhật

### ✅ File output

```
output_data/inventory_cleaned.csv
```

Format:

```
product_id,quantity
100,6821
101,5793
...
```

---

## 🧠 Xử lý lỗi dữ liệu

Dự án xử lý lỗi:

* **MISSING_VALUES** trong cột `quantity`

Cách xử lý:

* Chuyển về numeric
* Thay thế giá trị thiếu bằng **median**
* Loại bỏ giá trị âm

---

## ⚠️ Lưu ý

* ❌ Không chỉnh sửa file CSV bằng tay
* ✔ Tất cả xử lý phải qua code
* ✔ Có sử dụng try-except để đảm bảo chương trình không crash

---

## 🏁 Kết luận

Dự án đã hoàn thành:

* ✔ Data Cleaning
* ✔ Data Aggregation
* ✔ Database Update
* ✔ Data Export

👉 Đây là một pipeline ETL cơ bản (Extract - Transform - Load)

---

## 👨‍💻 Tác giả

* Nhóm 4
