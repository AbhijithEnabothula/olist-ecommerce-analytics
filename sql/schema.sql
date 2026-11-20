-- ============================================================================
-- Olist Brazilian E-Commerce Database Schema (MySQL 8.0+)
-- ============================================================================
CREATE DATABASE IF NOT EXISTS olist_ecommerce
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE olist_ecommerce;

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_category_translation;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS geolocation_zip_summary;

CREATE TABLE customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INT NOT NULL,
    customer_city VARCHAR(100) NOT NULL,
    customer_state CHAR(2) NOT NULL,
    INDEX idx_customer_unique (customer_unique_id),
    INDEX idx_customer_state (customer_state),
    INDEX idx_customer_zip (customer_zip_code_prefix)
);

CREATE TABLE sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix INT NOT NULL,
    seller_city VARCHAR(100) NOT NULL,
    seller_state CHAR(2) NOT NULL,
    INDEX idx_seller_state (seller_state),
    INDEX idx_seller_zip (seller_zip_code_prefix)
);

CREATE TABLE product_category_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(100) NULL,
    product_name_length INT NULL,
    product_description_length INT NULL,
    product_photos_qty INT NULL,
    product_weight_g DECIMAL(10, 2) NULL,
    product_length_cm DECIMAL(10, 2) NULL,
    product_height_cm DECIMAL(10, 2) NULL,
    product_width_cm DECIMAL(10, 2) NULL,
    INDEX idx_product_category (product_category_name)
);

CREATE TABLE orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(20) NOT NULL,
    order_purchase_timestamp DATETIME NOT NULL,
    order_approved_at DATETIME NULL,
    order_delivered_carrier_date DATETIME NULL,
    order_delivered_customer_date DATETIME NULL,
    order_estimated_delivery_date DATETIME NOT NULL,
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_order_status (order_status),
    INDEX idx_purchase_ts (order_purchase_timestamp)
);

CREATE TABLE order_items (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INT NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    seller_id VARCHAR(32) NOT NULL,
    shipping_limit_date DATETIME NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    freight_value DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_items_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT fk_items_seller FOREIGN KEY (seller_id) REFERENCES sellers(seller_id),
    INDEX idx_items_seller (seller_id),
    INDEX idx_items_product (product_id)
);

CREATE TABLE order_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(30) NOT NULL,
    payment_installments INT NOT NULL,
    payment_value DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_payment_type (payment_type)
);

CREATE TABLE order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score TINYINT NOT NULL,
    review_comment_title TEXT NULL,
    review_comment_message TEXT NULL,
    review_creation_date DATETIME NOT NULL,
    review_answer_timestamp DATETIME NULL,
    PRIMARY KEY (review_id, order_id),
    CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_review_score (review_score)
);

CREATE TABLE geolocation_zip_summary (
    geolocation_zip_code_prefix INT PRIMARY KEY,
    median_lat DECIMAL(10, 6) NOT NULL,
    median_lng DECIMAL(10, 6) NOT NULL,
    geolocation_city VARCHAR(100) NULL,
    geolocation_state CHAR(2) NULL
);

-- Example Bulk Load Command (run from project root with --local-infile=1):
-- LOAD DATA LOCAL INFILE 'data/raw/olist_customers_dataset.csv'
-- INTO TABLE customers FIELDS TERMINATED BY ',' ENCLOSED BY '"' LINES TERMINATED BY '
' IGNORE 1 ROWS;
