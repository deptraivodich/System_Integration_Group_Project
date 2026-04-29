"""
Module 2B: Order Worker - Consumer
=====================================
Lắng nghe liên tục từ RabbitMQ queue 'order_queue'
1. Consume message
2. Sleep 1-2s (giả lập payment processing)
3. INSERT vào PostgreSQL (Finance system)
4. UPDATE MySQL orders.status = 'COMPLETED'
5. ACK message → RabbitMQ xóa message khỏi queue
"""

import os
import json
import time
import random
import logging

import pika
import mysql.connector
import psycopg2
from psycopg2.extras import DictCursor

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
# MySQL (Web Store)
MYSQL_HOST     = os.getenv("DB_HOST", "mysql_db")
MYSQL_USER     = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "123456")
MYSQL_DB       = os.getenv("DB_NAME", "noah_retail")

# PostgreSQL (Finance)
PG_HOST     = os.getenv("PG_HOST", "postgres_db")
PG_PORT     = int(os.getenv("PG_PORT", "5432"))
PG_USER     = os.getenv("PG_USER", "postgres")
PG_PASSWORD = os.getenv("PG_PASSWORD", "postgres123")
PG_DB       = os.getenv("PG_DB", "noah_finance")

# RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME    = "order_queue"

MAX_RETRIES = 10
RETRY_DELAY = 5


# =========================
# RETRY HELPERS
# =========================
def get_mysql_connection():
    """Kết nối MySQL có cơ chế Retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[MySQL] Đang kết nối... (Lần {attempt}/{MAX_RETRIES})")
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                connection_timeout=10
            )
            logger.info("[MySQL] Kết nối thành công!")
            return conn
        except mysql.connector.Error as e:
            logger.warning(f"[MySQL] Lỗi: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise RuntimeError("Không thể kết nối MySQL!")


def get_postgres_connection():
    """Kết nối PostgreSQL có cơ chế Retry."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[PostgreSQL] Đang kết nối... (Lần {attempt}/{MAX_RETRIES})")
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                user=PG_USER,
                password=PG_PASSWORD,
                dbname=PG_DB,
                connect_timeout=10
            )
            logger.info("[PostgreSQL] Kết nối thành công!")
            return conn
        except psycopg2.OperationalError as e:
            logger.warning(f"[PostgreSQL] Lỗi: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise RuntimeError("Không thể kết nối PostgreSQL!")


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
            # Khai báo queue Durable (khớp với Producer)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            # Fair dispatch: chỉ nhận 1 message tại một thời điểm
            channel.basic_qos(prefetch_count=1)
            logger.info("[RabbitMQ] Kết nối thành công!")
            return connection, channel
        except pika.exceptions.AMQPConnectionError as e:
            logger.warning(f"[RabbitMQ] Lỗi: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
    raise RuntimeError("Không thể kết nối RabbitMQ!")


# =========================
# SETUP POSTGRES TABLE
# =========================
def ensure_transactions_table():
    """Tạo bảng transactions trong PostgreSQL nếu chưa có."""
    conn   = get_postgres_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id         SERIAL PRIMARY KEY,
                order_id   INT          NOT NULL,
                user_id    INT          NOT NULL,
                product_id INT          NOT NULL,
                quantity   INT          NOT NULL,
                amount     NUMERIC(12,2) DEFAULT 0,
                status     VARCHAR(20)  DEFAULT 'SYNCED',
                created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("[PostgreSQL] Bảng 'transactions' đã sẵn sàng.")
    finally:
        cursor.close()
        conn.close()


# =========================
# MESSAGE CALLBACK (XỬ LÝ ĐƠN HÀNG)
# =========================
def process_order(ch, method, properties, body):
    """
    Callback được gọi khi có message mới từ RabbitMQ.
    
    Flow:
    1. Parse JSON
    2. Sleep 1-2s (giả lập payment processing)
    3. INSERT vào PostgreSQL
    4. UPDATE MySQL status = COMPLETED
    5. ACK message (đảm bảo không mất message)
    """
    order_id   = None
    pg_conn    = None
    mysql_conn = None

    try:
        # Bước 1: Parse message
        data       = json.loads(body.decode("utf-8"))
        order_id   = data["order_id"]
        user_id    = data["user_id"]
        product_id = data["product_id"]
        quantity   = data["quantity"]

        logger.info(f"[Worker] Nhận được order_id={order_id} | user_id={user_id} | product_id={product_id} | qty={quantity}")

        # Bước 2: Giả lập độ trễ thanh toán phức tạp
        delay = random.uniform(1.0, 2.0)
        logger.info(f"[Worker] Đang xử lý thanh toán... (giả lập {delay:.1f}s)")
        time.sleep(delay)

        # Bước 3: Ghi vào PostgreSQL (Finance System)
        pg_conn    = get_postgres_connection()
        pg_cursor  = pg_conn.cursor()
        pg_cursor.execute(
            """
            INSERT INTO transactions (order_id, user_id, product_id, quantity, status)
            VALUES (%s, %s, %s, %s, 'SYNCED')
            """,
            (order_id, user_id, product_id, quantity)
        )
        pg_conn.commit()
        pg_cursor.close()
        logger.info(f"[PostgreSQL] Đã INSERT transaction cho order_id={order_id}")

        # Bước 4: Cập nhật MySQL status = COMPLETED
        mysql_conn   = get_mysql_connection()
        mysql_cursor = mysql_conn.cursor()
        mysql_cursor.execute(
            "UPDATE orders SET status = 'COMPLETED' WHERE id = %s",
            (order_id,)
        )
        mysql_conn.commit()
        mysql_cursor.close()
        logger.info(f"[MySQL] Đã UPDATE order_id={order_id} → COMPLETED")

        # Bước 5: ACK message (xóa khỏi queue)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[Worker] ✅ Order #{order_id} synced. ACK đã gửi.")

    except json.JSONDecodeError as e:
        logger.error(f"[Worker] ❌ Message không hợp lệ (JSON parse error): {e}")
        # NACK không requeue (message bị lỗi định dạng thì bỏ qua)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except Exception as e:
        logger.error(f"[Worker] ❌ Lỗi xử lý order_id={order_id}: {e}")
        # NACK và requeue để thử lại
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        logger.warning(f"[Worker] Message order_id={order_id} được đưa trở lại queue.")

    finally:
        if pg_conn and not pg_conn.closed:
            pg_conn.close()
        if mysql_conn and mysql_conn.is_connected():
            mysql_conn.close()


# =========================
# MAIN: START CONSUMING
# =========================
def start_worker():
    """Khởi động Worker lắng nghe RabbitMQ."""
    logger.info("=== Order Worker khởi động ===")

    # Chuẩn bị schema PostgreSQL
    ensure_transactions_table()

    # Kết nối và bắt đầu consume
    mq_conn, channel = get_rabbitmq_channel()

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=process_order,
        auto_ack=False   # Manual ACK để đảm bảo không mất message
    )

    logger.info(f"[Worker] 🎧 Đang lắng nghe queue '{QUEUE_NAME}'... Nhấn Ctrl+C để dừng.")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("[Worker] Dừng Worker theo yêu cầu.")
        channel.stop_consuming()
    except Exception as e:
        logger.error(f"[Worker] Lỗi nghiêm trọng: {e}")
    finally:
        if mq_conn and mq_conn.is_open:
            mq_conn.close()
        logger.info("[Worker] Đã tắt kết nối.")


if __name__ == "__main__":
    start_worker()
