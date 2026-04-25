"""
Tests cho Module 2B: Order Worker (Consumer)
=============================================
Chạy: python -m pytest tests/test_worker.py -v
Dùng mock để tránh phụ thuộc vào infrastructure thực.
"""

import json
import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock, call

# Thêm order_worker vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "order_worker"))


class TestWorkerProcessOrder(unittest.TestCase):
    """Test hàm process_order (callback xử lý message)."""

    def _make_mock_channel(self):
        """Tạo mock channel với ACK/NACK methods."""
        ch = MagicMock()
        ch.basic_ack  = MagicMock()
        ch.basic_nack = MagicMock()
        return ch

    def _make_mock_method(self, delivery_tag=1):
        """Tạo mock delivery method."""
        method              = MagicMock()
        method.delivery_tag = delivery_tag
        return method

    def test_valid_message_processed_successfully(self):
        """Message hợp lệ phải được xử lý và ACK."""
        with patch("mysql.connector.connect") as mock_mysql, \
             patch("psycopg2.connect") as mock_pg:

            # MySQL mock
            mysql_conn   = MagicMock()
            mysql_cursor = MagicMock()
            mysql_conn.cursor.return_value      = mysql_cursor
            mysql_conn.is_connected.return_value = True
            mock_mysql.return_value = mysql_conn

            # PostgreSQL mock
            pg_conn   = MagicMock()
            pg_cursor = MagicMock()
            pg_conn.cursor.return_value = pg_cursor
            pg_conn.closed             = False
            mock_pg.return_value       = pg_conn

            import importlib
            import worker
            importlib.reload(worker)

            ch     = self._make_mock_channel()
            method = self._make_mock_method(delivery_tag=5)
            body   = json.dumps({
                "order_id":   1,
                "user_id":    2,
                "product_id": 101,
                "quantity":   3
            }).encode("utf-8")

            worker.process_order(ch, method, None, body)

            # Phải gọi ACK
            ch.basic_ack.assert_called_once_with(delivery_tag=5)
            # Không được gọi NACK
            ch.basic_nack.assert_not_called()

    def test_postgres_insert_called(self):
        """Worker phải INSERT dữ liệu vào PostgreSQL."""
        with patch("mysql.connector.connect") as mock_mysql, \
             patch("psycopg2.connect") as mock_pg:

            mysql_conn   = MagicMock()
            mysql_cursor = MagicMock()
            mysql_conn.cursor.return_value      = mysql_cursor
            mysql_conn.is_connected.return_value = True
            mock_mysql.return_value = mysql_conn

            pg_conn   = MagicMock()
            pg_cursor = MagicMock()
            pg_conn.cursor.return_value = pg_cursor
            pg_conn.closed             = False
            mock_pg.return_value       = pg_conn

            import importlib
            import worker
            importlib.reload(worker)

            body = json.dumps({
                "order_id":   10,
                "user_id":    3,
                "product_id": 200,
                "quantity":   5
            }).encode("utf-8")

            worker.process_order(
                self._make_mock_channel(),
                self._make_mock_method(),
                None,
                body
            )

            # Kiểm tra pg_cursor.execute được gọi (INSERT)
            pg_cursor.execute.assert_called()
            # Kiểm tra pg_conn.commit được gọi
            pg_conn.commit.assert_called()

    def test_mysql_status_updated_to_completed(self):
        """Worker phải UPDATE MySQL status = COMPLETED."""
        with patch("mysql.connector.connect") as mock_mysql, \
             patch("psycopg2.connect") as mock_pg:

            mysql_conn   = MagicMock()
            mysql_cursor = MagicMock()
            mysql_conn.cursor.return_value      = mysql_cursor
            mysql_conn.is_connected.return_value = True
            mock_mysql.return_value = mysql_conn

            pg_conn   = MagicMock()
            pg_cursor = MagicMock()
            pg_conn.cursor.return_value = pg_cursor
            pg_conn.closed             = False
            mock_pg.return_value       = pg_conn

            import importlib
            import worker
            importlib.reload(worker)

            body = json.dumps({
                "order_id":   7,
                "user_id":    1,
                "product_id": 102,
                "quantity":   1
            }).encode("utf-8")

            worker.process_order(
                self._make_mock_channel(),
                self._make_mock_method(),
                None,
                body
            )

            # Kiểm tra mysql_cursor.execute được gọi với UPDATE COMPLETED
            all_calls = [str(c) for c in mysql_cursor.execute.call_args_list]
            has_update = any("COMPLETED" in c or "UPDATE" in c.upper() for c in all_calls)
            self.assertTrue(has_update,
                            f"MySQL UPDATE COMPLETED chưa được gọi. Calls: {all_calls}")

    def test_invalid_json_nack_no_requeue(self):
        """Message JSON không hợp lệ phải NACK (requeue=False)."""
        with patch("mysql.connector.connect"), \
             patch("psycopg2.connect"):

            import importlib
            import worker
            importlib.reload(worker)

            ch     = self._make_mock_channel()
            method = self._make_mock_method(delivery_tag=99)
            body   = b"this is not json at all!!!"

            worker.process_order(ch, method, None, body)

            # Phải NACK không requeue
            ch.basic_nack.assert_called_once_with(delivery_tag=99, requeue=False)
            # Không được ACK
            ch.basic_ack.assert_not_called()

    def test_message_missing_fields_causes_nack(self):
        """Message thiếu field (order_id missing) phải NACK với requeue=True."""
        with patch("mysql.connector.connect"), \
             patch("psycopg2.connect"):

            import importlib
            import worker
            importlib.reload(worker)

            ch     = self._make_mock_channel()
            method = self._make_mock_method(delivery_tag=50)
            body   = json.dumps({"user_id": 1}).encode("utf-8")  # thiếu order_id

            worker.process_order(ch, method, None, body)

            # Thiếu key → KeyError → NACK requeue=True
            ch.basic_nack.assert_called_once_with(delivery_tag=50, requeue=True)
            ch.basic_ack.assert_not_called()

    def test_processing_delay_applied(self):
        """Worker phải có delay 1-2 giây (giả lập thanh toán)."""
        with patch("mysql.connector.connect") as mock_mysql, \
             patch("psycopg2.connect") as mock_pg, \
             patch("time.sleep") as mock_sleep:

            mysql_conn   = MagicMock()
            mysql_cursor = MagicMock()
            mysql_conn.cursor.return_value      = mysql_cursor
            mysql_conn.is_connected.return_value = True
            mock_mysql.return_value = mysql_conn

            pg_conn   = MagicMock()
            pg_cursor = MagicMock()
            pg_conn.cursor.return_value = pg_cursor
            pg_conn.closed             = False
            mock_pg.return_value       = pg_conn

            import importlib
            import worker
            importlib.reload(worker)

            body = json.dumps({
                "order_id":   1,
                "user_id":    1,
                "product_id": 100,
                "quantity":   1
            }).encode("utf-8")

            worker.process_order(
                self._make_mock_channel(),
                self._make_mock_method(),
                None,
                body
            )

            # time.sleep phải được gọi ít nhất 1 lần
            mock_sleep.assert_called()
            # Và delay nằm trong khoảng 1-2 giây
            sleep_arg = mock_sleep.call_args[0][0]
            self.assertGreaterEqual(sleep_arg, 1.0,
                                    f"Delay quá ngắn: {sleep_arg}s (cần >= 1s)")
            self.assertLessEqual(sleep_arg, 2.0,
                                 f"Delay quá dài: {sleep_arg}s (cần <= 2s)")


class TestWorkerRetryConnection(unittest.TestCase):
    """Test cơ chế Retry Connection."""

    def test_mysql_retries_on_failure(self):
        """MySQL phải thử lại khi kết nối thất bại."""
        import importlib
        import worker
        importlib.reload(worker)

        import mysql.connector
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise mysql.connector.Error("Connection refused")
            # Thành công ở lần 3
            mock_conn   = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            return mock_conn

        with patch("mysql.connector.connect", side_effect=side_effect), \
             patch("time.sleep"):  # Skip actual sleep
            conn = worker.get_mysql_connection()
            self.assertIsNotNone(conn)
            self.assertEqual(call_count["n"], 3,
                             f"Phải thử 3 lần, thực tế: {call_count['n']}")

    def test_postgres_retries_on_failure(self):
        """PostgreSQL phải thử lại khi kết nối thất bại."""
        import importlib
        import worker
        importlib.reload(worker)

        import psycopg2
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise psycopg2.OperationalError("could not connect")
            mock_conn        = MagicMock()
            mock_conn.closed = False
            return mock_conn

        with patch("psycopg2.connect", side_effect=side_effect), \
             patch("time.sleep"):
            conn = worker.get_postgres_connection()
            self.assertIsNotNone(conn)
            self.assertEqual(call_count["n"], 2)

    def test_rabbitmq_retries_on_failure(self):
        """RabbitMQ phải thử lại khi kết nối thất bại."""
        import importlib
        import worker
        importlib.reload(worker)

        import pika
        call_count = {"n": 0}

        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 2:
                raise pika.exceptions.AMQPConnectionError("refused")
            mock_conn    = MagicMock()
            mock_conn.is_open = True
            mock_channel = MagicMock()
            mock_conn.channel.return_value = mock_channel
            return mock_conn

        with patch("pika.BlockingConnection", side_effect=side_effect), \
             patch("time.sleep"):
            conn, ch = worker.get_rabbitmq_channel()
            self.assertIsNotNone(conn)
            self.assertEqual(call_count["n"], 2)


class TestEnsureTransactionsTable(unittest.TestCase):
    """Test hàm ensure_transactions_table."""

    def test_table_creation_executed(self):
        """ensure_transactions_table phải gọi CREATE TABLE IF NOT EXISTS."""
        with patch("psycopg2.connect") as mock_pg:
            pg_conn   = MagicMock()
            pg_cursor = MagicMock()
            pg_conn.cursor.return_value = pg_cursor
            pg_conn.closed             = False
            mock_pg.return_value       = pg_conn

            import importlib
            import worker
            importlib.reload(worker)

            worker.ensure_transactions_table()

            pg_cursor.execute.assert_called()
            executed_sql = pg_cursor.execute.call_args[0][0]
            self.assertIn("CREATE TABLE IF NOT EXISTS transactions", executed_sql,
                          "Phải có lệnh CREATE TABLE IF NOT EXISTS transactions")
            pg_conn.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
