-- ============================================================================
-- Business, Seller, Category, and Late Delivery Analysis (MySQL 8.0+)
-- ============================================================================
USE olist_ecommerce;

-- 1. Executive KPI Summary (Orders with Line Items)
WITH order_revenue AS (
    SELECT
        oi.order_id,
        SUM(oi.price) AS item_revenue,
        SUM(oi.freight_value) AS freight_revenue
    FROM order_items oi
    GROUP BY oi.order_id
)
SELECT
    COUNT(DISTINCT orv.order_id) AS total_orders_with_items,
    (SELECT COUNT(DISTINCT seller_id) FROM sellers) AS total_sellers,
    ROUND(SUM(orv.item_revenue), 2) AS total_item_revenue,
    ROUND(SUM(orv.item_revenue + orv.freight_revenue), 2) AS total_gmv,
    ROUND(AVG(orv.item_revenue), 2) AS average_order_value
FROM order_revenue orv;

-- 2. Monthly Revenue, Order Volume & Month-over-Month Growth (Window Function)
WITH monthly_sales AS (
    SELECT
        DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m') AS purchase_month,
        COUNT(DISTINCT o.order_id) AS order_count,
        ROUND(SUM(oi.price), 2) AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status <> 'canceled'
    GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
)
SELECT
    purchase_month,
    order_count,
    monthly_revenue,
    LAG(monthly_revenue) OVER (ORDER BY purchase_month) AS prev_month_revenue,
    ROUND(
        100.0 * (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY purchase_month))
        / NULLIF(LAG(monthly_revenue) OVER (ORDER BY purchase_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly_sales
ORDER BY purchase_month;

-- 3. Top 10 Product Categories by Revenue & Late Delivery Rate
WITH delivered_items AS (
    SELECT
        oi.order_id,
        COALESCE(pct.product_category_name_english, p.product_category_name, 'unknown') AS category_english,
        oi.price,
        CASE
            WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1
            ELSE 0
        END AS is_late
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN products p ON oi.product_id = p.product_id
    LEFT JOIN product_category_translation pct ON p.product_category_name = pct.product_category_name
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
)
SELECT
    category_english,
    COUNT(DISTINCT order_id) AS delivered_orders,
    ROUND(SUM(price), 2) AS category_revenue,
    ROUND(100.0 * AVG(is_late), 2) AS late_delivery_rate_pct
FROM delivered_items
GROUP BY category_english
ORDER BY category_revenue DESC
LIMIT 10;

-- 4. Seller Performance Ranking (Minimum 50 Delivered Orders)
WITH seller_orders AS (
    SELECT
        oi.seller_id,
        s.seller_state,
        oi.order_id,
        SUM(oi.price) AS seller_order_revenue,
        MAX(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END) AS is_late
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY oi.seller_id, s.seller_state, oi.order_id
)
SELECT
    seller_id,
    seller_state,
    COUNT(*) AS delivered_orders,
    ROUND(SUM(seller_order_revenue), 2) AS total_revenue,
    ROUND(100.0 * AVG(is_late), 2) AS late_rate_pct,
    RANK() OVER (ORDER BY SUM(seller_order_revenue) DESC) AS revenue_rank
FROM seller_orders
GROUP BY seller_id, seller_state
HAVING COUNT(*) >= 50
ORDER BY total_revenue DESC
LIMIT 15;

-- 5. Impact of Delivery Delays on Customer Review Scores
WITH order_reviews_agg AS (
    SELECT order_id, AVG(review_score) AS avg_review_score
    FROM order_reviews
    GROUP BY order_id
)
SELECT
    CASE
        WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 'On-Time / Early'
        ELSE 'Late Delivery'
    END AS delivery_sla_status,
    COUNT(*) AS order_count,
    ROUND(AVG(TIMESTAMPDIFF(HOUR, o.order_purchase_timestamp, o.order_delivered_customer_date) / 24.0), 2) AS avg_delivery_days,
    ROUND(AVG(r.avg_review_score), 2) AS avg_review_score
FROM orders o
JOIN order_reviews_agg r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY delivery_sla_status;
