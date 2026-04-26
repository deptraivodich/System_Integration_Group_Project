import os
import time
from fastapi import FastAPI, HTTPException
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

app = FastAPI(title="NOAH Retail - Report API")

# Lấy cấu hình từ biến môi trường
MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql_db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres_db")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASS = os.getenv("MYSQL_PASS", "123456")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASS = os.getenv("POSTGRES_PASS", "postgres123")

# Connection URIs
MYSQL_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:3306/noah_retail"
POSTGRES_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:5432/noah_finance"

def get_engine_with_retry(uri, name, retries=10, delay=5):
    for i in range(retries):
        try:
            engine = create_engine(uri)
            # Kiểm tra kết nối nhanh
            with engine.connect() as conn:
                pass
            print(f"[{name}] Connected successfully.")
            return engine
        except OperationalError as e:
            print(f"[{name}] Connection failed (attempt {i+1}/{retries}): {e}")
            time.sleep(delay)
    raise Exception(f"Cannot connect to {name} after {retries} retries")

# Khởi tạo DB Engines (Sẽ thực thi khi có request đầu tiên hoặc startup)
mysql_engine = None
postgres_engine = None

@app.on_event("startup")
def startup_event():
    global mysql_engine, postgres_engine
    # Tạo kết nối bền vững khi service khởi động
    mysql_engine = get_engine_with_retry(MYSQL_URI, "MySQL")
    postgres_engine = get_engine_with_retry(POSTGRES_URI, "PostgreSQL")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "report_api"}

@app.get("/api/report")
def get_report(page: int = 1, limit: int = 20):
    try:
        offset = (page - 1) * limit
        
        # 1. Lấy dữ liệu orders từ MySQL
        orders_query = f"""
            SELECT id as order_id, user_id, product_id, quantity, status
            FROM orders
            ORDER BY id DESC
            LIMIT {limit} OFFSET {offset}
        """
        orders_df = pd.read_sql(orders_query, mysql_engine)
        
        if orders_df.empty:
            return {"orders": [], "revenue_by_user": [], "pagination": {"page": page, "limit": limit}}

        # Lấy danh sách order_id để query Postgres
        order_ids = tuple(orders_df['order_id'].tolist())
        if len(order_ids) == 1:
            order_ids_str = f"({order_ids[0]})"
        else:
            order_ids_str = str(order_ids)

        # 2. Lấy dữ liệu transactions tương ứng từ PostgreSQL
        transactions_query = f"""
            SELECT order_id, amount, status as payment_status
            FROM transactions
            WHERE order_id IN {order_ids_str}
        """
        transactions_df = pd.read_sql(transactions_query, postgres_engine)

        # 3. Data Stitching (JOIN)
        if not transactions_df.empty:
            merged_df = pd.merge(
                orders_df,
                transactions_df,
                on="order_id",
                how="left"
            )
        else:
            merged_df = orders_df.copy()
            merged_df['amount'] = 0.0
            merged_df['payment_status'] = "UNKNOWN"

        # Đảm bảo NaN được thay bằng giá trị mặc định cho JSON chuẩn
        merged_df['amount'] = merged_df['amount'].fillna(0.0)
        merged_df['payment_status'] = merged_df['payment_status'].fillna("PENDING")

        # 4. Tính toán tổng quan (trên bộ dữ liệu hiện tại, thực tế có thể query riêng để lấy toàn cục)
        # Để cho nhanh và đơn giản, tính luôn tổng doanh thu của limit này
        revenue_by_user = merged_df.groupby("user_id")["amount"].sum().reset_index()

        # 5. Định dạng JSON trả về
        return {
            "orders": merged_df.to_dict(orient="records"),
            "revenue_by_user": revenue_by_user.to_dict(orient="records"),
            "pagination": {
                "page": page,
                "limit": limit
            }
        }
    except Exception as e:
        print(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
