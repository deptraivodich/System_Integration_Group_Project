"""
Tests cho Module 2A: Order API
================================
Chạy: python -m pytest tests/test_order_api.py -v
Lưu ý: Các unittest này chạy độc lập (không cần Docker), dùng mock.
"""

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

# Thêm module_api vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "order_api"))


class TestOrderRequestValidation(unittest.TestCase):
    """Test validation logic của Pydantic model."""

    def setUp(self):
        """Import sau khi patch để tránh side effects."""
        # Patch mysql và pika trước khi import app
        self.mysql_patch   = patch("mysql.connector.connect")
        self.pika_patch    = patch("pika.BlockingConnection")
        self.mysql_mock    = self.mysql_patch.start()
        self.pika_mock     = self.pika_patch.start()

        # Mock connection objects
        mock_conn   = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_conn.cursor.return_value = mock_cursor
        self.mysql_mock.return_value = mock_conn

        mock_mq_conn    = MagicMock()
        mock_mq_conn.is_open = True
        mock_channel    = MagicMock()
        mock_mq_conn.channel.return_value = mock_channel
        self.pika_mock.return_value = mock_mq_conn

    def tearDown(self):
        self.mysql_patch.stop()
        self.pika_patch.stop()

    def test_valid_order_payload(self):
        """Payload hợp lệ nên pass validation."""
        from pydantic import ValidationError
        # Import model trực tiếp
        import importlib
        import app as order_app
        importlib.reload(order_app)

        payload = {"user_id": 1, "product_id": 101, "quantity": 2}
        model = order_app.OrderRequest(**payload)
        self.assertEqual(model.user_id, 1)
        self.assertEqual(model.product_id, 101)
        self.assertEqual(model.quantity, 2)

    def test_quantity_zero_rejected(self):
        """quantity = 0 phải bị từ chối."""
        from pydantic import ValidationError
        import importlib
        import app as order_app
        importlib.reload(order_app)

        with self.assertRaises(ValidationError):
            order_app.OrderRequest(user_id=1, product_id=101, quantity=0)

    def test_quantity_negative_rejected(self):
        """quantity âm phải bị từ chối."""
        from pydantic import ValidationError
        import importlib
        import app as order_app
        importlib.reload(order_app)

        with self.assertRaises(ValidationError):
            order_app.OrderRequest(user_id=1, product_id=101, quantity=-5)

    def test_user_id_zero_rejected(self):
        """user_id = 0 phải bị từ chối."""
        from pydantic import ValidationError
        import importlib
        import app as order_app
        importlib.reload(order_app)

        with self.assertRaises(ValidationError):
            order_app.OrderRequest(user_id=0, product_id=101, quantity=2)

    def test_product_id_negative_rejected(self):
        """product_id âm phải bị từ chối."""
        from pydantic import ValidationError
        import importlib
        import app as order_app
        importlib.reload(order_app)

        with self.assertRaises(ValidationError):
            order_app.OrderRequest(user_id=1, product_id=-1, quantity=2)


class TestOrderAPIEndpoints(unittest.TestCase):
    """Test HTTP endpoints của Order API bằng FastAPI TestClient."""

    def setUp(self):
        """Patch tất cả kết nối DB/MQ trước khi khởi tạo TestClient."""
        self.mysql_patch = patch("mysql.connector.connect")
        self.pika_patch  = patch("pika.BlockingConnection")

        self.mysql_mock = self.mysql_patch.start()
        self.pika_mock  = self.pika_patch.start()

        # Setup MySQL mock
        mock_conn        = MagicMock()
        mock_cursor      = MagicMock()
        mock_cursor.lastrowid = 42
        mock_cursor.fetchone.return_value = {
            "id": 42, "user_id": 1, "product_id": 101,
            "quantity": 2, "status": "PENDING", "created_at": "2026-01-01 00:00:00"
        }
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.is_connected.return_value = True
        self.mysql_mock.return_value = mock_conn

        # Setup RabbitMQ mock
        mock_mq_conn    = MagicMock()
        mock_mq_conn.is_open = True
        mock_channel    = MagicMock()
        mock_mq_conn.channel.return_value = mock_channel
        self.pika_mock.return_value = mock_mq_conn

        import importlib
        import app as order_app
        importlib.reload(order_app)

        from fastapi.testclient import TestClient
        # Tránh gọi lifespan (ensure_orders_table) trong test
        with patch.object(order_app, "ensure_orders_table"):
            self.client = TestClient(order_app.app, raise_server_exceptions=False)

    def tearDown(self):
        self.mysql_patch.stop()
        self.pika_patch.stop()

    def test_health_endpoint(self):
        """GET /health phải trả về 200 OK."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "order_api")

    def test_create_order_returns_202(self):
        """POST /api/orders hợp lệ phải trả về 202."""
        payload  = {"user_id": 1, "product_id": 101, "quantity": 2}
        response = self.client.post("/api/orders", json=payload)
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertIn("order_id", data)
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Order received")
        self.assertEqual(data["status"], "PENDING")

    def test_create_order_quantity_zero_returns_422(self):
        """POST /api/orders với quantity=0 phải trả về 422 Unprocessable Entity."""
        payload  = {"user_id": 1, "product_id": 101, "quantity": 0}
        response = self.client.post("/api/orders", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_create_order_quantity_negative_returns_422(self):
        """POST /api/orders với quantity âm phải trả về 422."""
        payload  = {"user_id": 1, "product_id": 101, "quantity": -3}
        response = self.client.post("/api/orders", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_create_order_missing_field_returns_422(self):
        """POST /api/orders thiếu field phải trả về 422."""
        payload  = {"user_id": 1, "quantity": 2}  # thiếu product_id
        response = self.client.post("/api/orders", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_create_order_empty_body_returns_422(self):
        """POST /api/orders body rỗng phải trả về 422."""
        response = self.client.post("/api/orders", json={})
        self.assertEqual(response.status_code, 422)

    def test_response_has_correct_fields(self):
        """Response phải có đầy đủ các field theo đặc tả."""
        payload  = {"user_id": 3, "product_id": 105, "quantity": 10}
        response = self.client.post("/api/orders", json=payload)
        self.assertEqual(response.status_code, 202)
        data = response.json()
        required_fields = {"message", "order_id", "status"}
        self.assertTrue(required_fields.issubset(data.keys()),
                        f"Thiếu field trong response: {required_fields - data.keys()}")


class TestOrderAPIRabbitMQIntegration(unittest.TestCase):
    """Test tích hợp: API → RabbitMQ message format."""

    def test_message_format_is_correct(self):
        """Message gửi lên RabbitMQ phải đúng format JSON."""
        published_messages = []

        with patch("mysql.connector.connect") as mock_mysql, \
             patch("pika.BlockingConnection") as mock_pika:

            # MySQL mock
            mock_conn   = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.lastrowid = 99
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.is_connected.return_value = True
            mock_mysql.return_value = mock_conn

            # RabbitMQ mock — bắt message được publish
            mock_mq_conn = MagicMock()
            mock_mq_conn.is_open = True
            mock_channel = MagicMock()

            def capture_publish(exchange, routing_key, body, properties):
                published_messages.append(json.loads(body))

            mock_channel.basic_publish.side_effect = capture_publish
            mock_mq_conn.channel.return_value = mock_channel
            mock_pika.return_value = mock_mq_conn

            import importlib
            import app as order_app
            importlib.reload(order_app)

            from fastapi.testclient import TestClient
            with patch.object(order_app, "ensure_orders_table"):
                client = TestClient(order_app.app, raise_server_exceptions=False)

            payload  = {"user_id": 5, "product_id": 200, "quantity": 3}
            response = client.post("/api/orders", json=payload)

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(published_messages), 1,
                         "Phải publish đúng 1 message vào RabbitMQ")

        msg = published_messages[0]
        self.assertIn("order_id",   msg)
        self.assertIn("user_id",    msg)
        self.assertIn("product_id", msg)
        self.assertIn("quantity",   msg)
        self.assertEqual(msg["user_id"],    5)
        self.assertEqual(msg["product_id"], 200)
        self.assertEqual(msg["quantity"],   3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
