"""
Module 2A: Order API - Producer
================================
Nhận đơn hàng qua HTTP POST /api/orders
1. Validate dữ liệu đầu vào
2. Ghi nhận vào MySQL với trạng thái PENDING
3. Publish message vào RabbitMQ (order_queue)
4. Trả về phản hồi 202 ngay lập tức (không chờ xử lý)
"""

import os
import json
import time
import logging
from contextlib import asynccontextmanager

import pika
import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

# =========================
# LOGGING SETUP
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# CẤU HÌNH MÔI TRƯỜNG
# =========================
DB_HOST     = os.getenv("DB_HOST", "mysql_db")
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_NAME     = os.getenv("DB_NAME", "noah_retail")

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME    = "order_queue"

MAX_RETRIES   = 10
RETRY_DELAY   = 5

# =========================
# INPUT MODEL (PYDANTIC)
# =========================
class OrderRequest(BaseModel):
    user_id: int
    product_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity phải lớn hơn 0")
        return v

    @field_validator("user_id", "product_id")
    @classmethod
    def ids_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("user_id và product_id phải lớn hơn 0")
        return v


# =========================
# RETRY HELPERS
# =========================
def get_mysql_connection():
    """Kết nối MySQL có cơ chế Retry (Retry Challenge requirement)."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[MySQL] Đang kết nối... (Lần {attempt}/{MAX_RETRIES})")
            conn = mysql.connector.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                connection_timeout=10
            )
            logger.info("[MySQL] Kết nối thành công!")
            return conn
        except mysql.connector.Error as e:
            logger.warning(f"[MySQL] Lỗi kết nối: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"[MySQL] Thử lại sau {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
    raise RuntimeError("Không thể kết nối MySQL sau nhiều lần thử!")


def get_rabbitmq_channel():
    """Kết nối RabbitMQ có cơ chế Retry."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters  = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=5672,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[RabbitMQ] Đang kết nối... (Lần {attempt}/{MAX_RETRIES})")
            connection = pika.BlockingConnection(parameters)
            channel    = connection.channel()
            # Khai báo queue Durable (tin nhắn không mất khi RabbitMQ restart)
            channel.queue_declare(
                queue=QUEUE_NAME,
                durable=True
            )
            logger.info("[RabbitMQ] Kết nối thành công!")
            return connection, channel
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"[RabbitMQ] Lỗi kết nối: {e}")
            if attempt < MAX_RETRIES:
                logger.info(f"[RabbitMQ] Thử lại sau {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
    raise RuntimeError("Không thể kết nối RabbitMQ sau nhiều lần thử!")


# =========================
# LIFESPAN (khởi tạo kết nối DB khi startup)
# =========================
def ensure_orders_table():
    """Tạo bảng orders nếu chưa tồn tại."""
    conn = get_mysql_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                user_id     INT NOT NULL,
                product_id  INT NOT NULL,
                quantity    INT NOT NULL,
                status      ENUM('PENDING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("[MySQL] Bảng 'orders' đã sẵn sàng.")
    finally:
        cursor.close()
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Chạy khi app startup: đảm bảo DB sẵn sàng."""
    logger.info("=== Order API đang khởi động ===")
    ensure_orders_table()
    yield
    logger.info("=== Order API đang tắt ===")


# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    title="NOAH Retail - Order API",
    description="Module 2A: Nhận đơn hàng và đẩy vào RabbitMQ queue",
    version="1.0.0",
    lifespan=lifespan
)


# =========================
# ENDPOINTS
# =========================
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "order_api"}


@app.post("/api/orders", status_code=202)
def create_order(order: OrderRequest):
    """
    Nhận đơn hàng từ client.
    
    Flow:
    1. Validate input (Pydantic tự động)
    2. INSERT vào MySQL với status = PENDING
    3. Publish message vào RabbitMQ order_queue
    4. Trả về 202 Accepted ngay lập tức
    """
    order_id = None

    # --- BƯỚC 1 & 2: Ghi vào MySQL ---
    conn   = None
    cursor = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO orders (user_id, product_id, quantity, status)
            VALUES (%s, %s, %s, 'PENDING')
            """,
            (order.user_id, order.product_id, order.quantity)
        )
        conn.commit()
        order_id = cursor.lastrowid
        logger.info(f"[MySQL] Đã tạo order_id={order_id} với trạng thái PENDING")

    except mysql.connector.Error as e:
        logger.error(f"[MySQL] Lỗi INSERT: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi Database: {str(e)}")
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()

    # --- BƯỚC 3: Publish lên RabbitMQ ---
    mq_conn    = None
    mq_channel = None
    try:
        mq_conn, mq_channel = get_rabbitmq_channel()

        message_body = json.dumps({
            "order_id":   order_id,
            "user_id":    order.user_id,
            "product_id": order.product_id,
            "quantity":   order.quantity
        })

        mq_channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,   # Persistent message - không mất khi RabbitMQ restart
                content_type="application/json"
            )
        )
        logger.info(f"[RabbitMQ] Đã publish order_id={order_id} vào queue '{QUEUE_NAME}'")

    except Exception as e:
        logger.error(f"[RabbitMQ] Lỗi publish: {e}")
        # Cập nhật trạng thái FAILED nếu không publish được
        try:
            fail_conn   = get_mysql_connection()
            fail_cursor = fail_conn.cursor()
            fail_cursor.execute(
                "UPDATE orders SET status = 'FAILED' WHERE id = %s",
                (order_id,)
            )
            fail_conn.commit()
            fail_cursor.close()
            fail_conn.close()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Lỗi Queue: {str(e)}")
    finally:
        if mq_conn and mq_conn.is_open:
            mq_conn.close()

    # --- BƯỚC 4: Trả về ngay lập tức (không chờ worker xử lý) ---
    logger.info(f"[API] Đã phản hồi 202 cho order_id={order_id}")
    return JSONResponse(
        status_code=202,
        content={
            "message":  "Order received",
            "order_id": order_id,
            "status":   "PENDING"
        }
    )


@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    """Kiểm tra trạng thái đơn hàng theo ID."""
    conn   = None
    cursor = None
    try:
        conn   = get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, user_id, product_id, quantity, status, created_at FROM orders WHERE id = %s",
            (order_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy order_id={order_id}")
        # Chuyển datetime thành string
        row["created_at"] = str(row["created_at"])
        return row
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor: cursor.close()
        if conn:   conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False)
