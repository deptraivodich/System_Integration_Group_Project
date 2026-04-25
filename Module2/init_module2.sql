-- Module 2: Tạo bảng orders trong Database noah_retail
-- (Chạy sau init.sql của Module 1)

USE noah_retail;

CREATE TABLE IF NOT EXISTS orders (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    product_id  INT NOT NULL,
    quantity    INT NOT NULL,
    status      ENUM('PENDING', 'COMPLETED', 'FAILED') DEFAULT 'PENDING',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status     (status),
    INDEX idx_user_id    (user_id),
    INDEX idx_product_id (product_id)
);
