-- ============================================================================
-- Data Quality & Referential Integrity Audit Queries (MySQL 8.0+)
-- ============================================================================
USE olist_ecommerce;

-- 1. Row Counts Across Core Tables
SELECT 'orders' AS table_name, COUNT(*) AS row_count FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'customers', COUNT(*) FROM customers
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'products', COUNT(*) FROM products;

-- 2. Missing Timestamp Audit on Delivered Orders
SELECT
    COUNT(*) AS total_delivered_orders,
    SUM(CASE WHEN order_approved_at IS NULL THEN 1 ELSE 0 END) AS missing_approved_at,
    SUM(CASE WHEN order_delivered_carrier_date IS NULL THEN 1 ELSE 0 END) AS missing_carrier_date,
    SUM(CASE WHEN order_delivered_customer_date IS NULL THEN 1 ELSE 0 END) AS missing_customer_date
FROM orders
WHERE order_status = 'delivered';

-- 3. Detect Chronological Timestamp Anomalies (Delivered Before Purchase)
SELECT
    order_id,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_customer_date
FROM orders
WHERE order_delivered_customer_date < order_purchase_timestamp
   OR order_approved_at < order_purchase_timestamp;

-- 4. Multi-Row Grain Check (Orders with Multiple Items, Sellers, Payments, or Reviews)
SELECT
    (SELECT COUNT(*) FROM (SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(*) > 1) t1) AS multi_item_orders,
    (SELECT COUNT(*) FROM (SELECT order_id FROM order_items GROUP BY order_id HAVING COUNT(DISTINCT seller_id) > 1) t2) AS multi_seller_orders,
    (SELECT COUNT(*) FROM (SELECT order_id FROM order_payments GROUP BY order_id HAVING COUNT(*) > 1) t3) AS multi_payment_orders,
    (SELECT COUNT(*) FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1) t4) AS multi_review_orders;

-- 5. Negative or Zero Price / Freight Validation
SELECT
    SUM(CASE WHEN price <= 0 THEN 1 ELSE 0 END) AS non_positive_price_rows,
    SUM(CASE WHEN freight_value < 0 THEN 1 ELSE 0 END) AS negative_freight_rows
FROM order_items;
