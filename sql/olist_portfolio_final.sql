USE olist_analysis;


/* ============================================================
   OLIST E-COMMERCE ANALYTICS
   FINAL SQL PORTFOLIO
   ============================================================

   Purpose:
   Business-focused SQL analysis of the Olist e-commerce dataset.

   Important grain:
   fact_sales = one row per order item

   Therefore:
   - Revenue is calculated from price at item level.
   - Orders use COUNT(DISTINCT order_id).
   - Delivery/customer analysis uses appropriate order-level logic.
   - Payments are handled separately because an order can have
     multiple payment records.

   Important limitation:
   The dataset does NOT contain COGS/profit data.
   Therefore freight/revenue is NOT treated as profit or profitability.

   ============================================================ */


/* ============================================================
   1. DATA VALIDATION & GRAIN CHECK
   Business Question:
   Are the core tables loaded correctly and does fact_sales
   have the expected grain?
   ============================================================ */

SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT order_id) AS unique_orders,
    COUNT(DISTINCT product_id) AS unique_products,
    COUNT(DISTINCT seller_id) AS unique_sellers
FROM fact_sales;


/* ============================================================
   2. EXECUTIVE SALES KPIs
   Business Question:
   What is the overall scale and performance of the marketplace?
   ============================================================ */

SELECT
    ROUND(SUM(price), 2) AS total_revenue,
    COUNT(DISTINCT order_id) AS total_orders,
    COUNT(*) AS total_items,
    COUNT(DISTINCT product_id) AS unique_products,
    COUNT(DISTINCT seller_id) AS unique_sellers,
    COUNT(DISTINCT product_category_name_english) AS categories,

    ROUND(
        SUM(price) / COUNT(DISTINCT order_id),
        2
    ) AS average_order_value,

    ROUND(AVG(price), 2) AS average_item_price,

    ROUND(AVG(freight_value), 2) AS average_freight_per_item,

    ROUND(
        SUM(freight_value) / SUM(price) * 100,
        2
    ) AS freight_to_revenue_percentage

FROM fact_sales;


/* ============================================================
   3. MONTHLY REVENUE + MONTH-OVER-MONTH GROWTH
   Business Question:
   How did marketplace revenue change over time?
   ============================================================ */

WITH monthly_sales AS (

    SELECT
        DATE_FORMAT(
            order_purchase_timestamp,
            '%Y-%m'
        ) AS order_month,

        SUM(price) AS revenue,

        COUNT(DISTINCT order_id) AS orders

    FROM fact_sales

    GROUP BY
        DATE_FORMAT(
            order_purchase_timestamp,
            '%Y-%m'
        )
),

monthly_growth AS (

    SELECT
        order_month,
        revenue,
        orders,

        LAG(revenue) OVER (
            ORDER BY order_month
        ) AS previous_month_revenue

    FROM monthly_sales
)

SELECT
    order_month,

    ROUND(revenue, 2) AS revenue,

    orders,

    ROUND(
        (revenue - previous_month_revenue)
        / NULLIF(previous_month_revenue, 0)
        * 100,
        2
    ) AS revenue_growth_percentage

FROM monthly_growth

ORDER BY order_month;


/* ============================================================
   4. CATEGORY PERFORMANCE & REVENUE SHARE
   Business Question:
   Which categories contribute most to marketplace revenue?
   ============================================================ */

WITH category_sales AS (

    SELECT
        product_category_name_english AS category,

        SUM(price) AS revenue,

        COUNT(DISTINCT order_id) AS orders,

        COUNT(*) AS items

    FROM fact_sales

    GROUP BY
        product_category_name_english
)

SELECT
    category,

    ROUND(revenue, 2) AS revenue,

    orders,

    items,

    ROUND(
        revenue / SUM(revenue) OVER () * 100,
        2
    ) AS revenue_share_percentage

FROM category_sales

ORDER BY revenue DESC;


/* ============================================================
   5. CATEGORY RANKING
   Business Question:
   How do categories rank by revenue?
   ============================================================ */

WITH category_sales AS (

    SELECT
        product_category_name_english AS category,

        SUM(price) AS revenue,

        COUNT(DISTINCT order_id) AS orders

    FROM fact_sales

    GROUP BY
        product_category_name_english
),

ranked_categories AS (

    SELECT
        category,
        revenue,
        orders,

        RANK() OVER (
            ORDER BY revenue DESC
        ) AS revenue_rank

    FROM category_sales
)

SELECT
    revenue_rank,
    category,
    ROUND(revenue, 2) AS revenue,
    orders

FROM ranked_categories

ORDER BY revenue_rank;


/* ============================================================
   6. TOP 3 PRODUCTS WITHIN EACH CATEGORY
   Business Question:
   Which products are the strongest revenue generators
   within each category?
   ============================================================ */

WITH product_sales AS (

    SELECT
        product_category_name_english AS category,

        product_id,

        SUM(price) AS revenue,

        COUNT(*) AS items

    FROM fact_sales

    GROUP BY
        product_category_name_english,
        product_id
),

ranked_products AS (

    SELECT
        category,
        product_id,
        revenue,
        items,

        ROW_NUMBER() OVER (
            PARTITION BY category
            ORDER BY revenue DESC
        ) AS product_rank

    FROM product_sales
)

SELECT
    category,
    product_id,

    ROUND(revenue, 2) AS revenue,

    items,

    product_rank

FROM ranked_products

WHERE product_rank <= 3

ORDER BY
    category,
    product_rank;


/* ============================================================
   7. SELLER CONCENTRATION
   Business Question:
   How dependent is marketplace revenue on the largest sellers?
   ============================================================ */

WITH seller_sales AS (

    SELECT
        seller_id,

        SUM(price) AS revenue

    FROM fact_sales

    GROUP BY seller_id
),

seller_ranked AS (

    SELECT
        seller_id,
        revenue,

        ROW_NUMBER() OVER (
            ORDER BY revenue DESC
        ) AS seller_rank

    FROM seller_sales
),

seller_cumulative AS (

    SELECT
        seller_id,
        revenue,
        seller_rank,

        SUM(revenue) OVER (
            ORDER BY seller_rank
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        ) AS cumulative_revenue

    FROM seller_ranked
),

total_marketplace AS (

    SELECT
        SUM(price) AS total_revenue

    FROM fact_sales
)

SELECT
    seller_rank,

    seller_id,

    ROUND(revenue, 2) AS seller_revenue,

    ROUND(
        revenue / total_revenue * 100,
        2
    ) AS revenue_share_percentage,

    ROUND(
        cumulative_revenue / total_revenue * 100,
        2
    ) AS cumulative_revenue_share_percentage

FROM seller_cumulative
CROSS JOIN total_marketplace

WHERE seller_rank <= 100

ORDER BY seller_rank;


/* ============================================================
   8. HIGH-REVENUE + HIGH-FREIGHT SELLERS
   Business Question:
   Which important sellers may require logistics optimization?

   Threshold:
   - Revenue >= $50,000
   - At least 100 orders
   - Freight >= 20% of revenue

   Note:
   This identifies logistics-cost opportunities.
   It does NOT measure seller profitability.
   ============================================================ */

SELECT
    seller_id,

    ROUND(SUM(price), 2) AS revenue,

    COUNT(DISTINCT order_id) AS orders,

    ROUND(
        SUM(freight_value),
        2
    ) AS freight,

    ROUND(
        SUM(freight_value) /
        NULLIF(SUM(price), 0) * 100,
        2
    ) AS freight_percentage

FROM fact_sales

GROUP BY seller_id

HAVING
    SUM(price) >= 50000
    AND COUNT(DISTINCT order_id) >= 100
    AND SUM(freight_value) /
        NULLIF(SUM(price), 0) >= 0.20

ORDER BY revenue DESC;


/* ============================================================
   9. OVERALL DELIVERY PERFORMANCE
   Business Question:
   How reliable is the marketplace delivery operation?

   Uses orders_clean because delivery performance is
   fundamentally an order-level metric.
   ============================================================ */

SELECT

    COUNT(*) AS total_orders,

    SUM(
        CASE
            WHEN order_status = 'delivered'
            THEN 1
            ELSE 0
        END
    ) AS delivered_orders,

    SUM(
        CASE
            WHEN delivery_status = 'late'
            THEN 1
            ELSE 0
        END
    ) AS late_orders,

    SUM(
        CASE
            WHEN delivery_status = 'not_delivered'
            THEN 1
            ELSE 0
        END
    ) AS not_delivered_orders,

    ROUND(
        AVG(delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        SUM(
            CASE
                WHEN delivery_status = 'late'
                THEN 1
                ELSE 0
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN order_status = 'delivered'
                    THEN 1
                    ELSE 0
                END
            ),
            0
        ) * 100,
        2
    ) AS late_rate_percentage

FROM orders_clean;


/* ============================================================
   10. HIGH-REVENUE STATES WITH DELIVERY RISK
   Business Question:
   Which customer states combine meaningful revenue
   with elevated late-delivery rates?

   Threshold:
   - Revenue >= $150,000
   - Orders >= 500
   - Late rate >= 10%

   fact_sales is used for revenue.
   Distinct orders are used for delivery rate.
   ============================================================ */

WITH state_sales AS (

    SELECT
        c.customer_state AS state,

        SUM(f.price) AS revenue,

        COUNT(DISTINCT f.order_id) AS orders,

        COUNT(
            DISTINCT
            CASE
                WHEN f.is_late = 1
                THEN f.order_id
            END
        ) AS late_orders

    FROM fact_sales f

    JOIN customers_clean c
        ON f.customer_id = c.customer_id

    GROUP BY c.customer_state
)

SELECT
    state,

    ROUND(revenue, 2) AS revenue,

    orders,

    late_orders,

    ROUND(
        late_orders /
        NULLIF(orders, 0) * 100,
        2
    ) AS late_rate_percentage

FROM state_sales

WHERE
    revenue >= 150000
    AND orders >= 500
    AND late_orders /
        NULLIF(orders, 0) >= 0.10

ORDER BY revenue DESC;


/* ============================================================
   11. DELIVERY PERFORMANCE VS CUSTOMER SATISFACTION
   Business Question:
   Is there an association between delivery performance
   and review scores?

   Reviews are first aggregated to order level to avoid
   accidental multiplication during joins.
   ============================================================ */

WITH order_reviews AS (

    SELECT
        order_id,

        AVG(review_score) AS review_score

    FROM reviews_clean

    GROUP BY order_id
)

SELECT
    o.delivery_status,

    COUNT(DISTINCT o.order_id) AS orders,

    ROUND(
        AVG(r.review_score),
        2
    ) AS average_review_score,

    ROUND(
        SUM(
            CASE
                WHEN r.review_score = 1
                THEN 1
                ELSE 0
            END
        )
        /
        NULLIF(
            COUNT(r.review_score),
            0
        ) * 100,
        2
    ) AS one_star_percentage

FROM orders_clean o

LEFT JOIN order_reviews r
    ON o.order_id = r.order_id

GROUP BY
    o.delivery_status

ORDER BY
    average_review_score DESC;


/* ============================================================
   12. PAYMENT METHOD PERFORMANCE
   Business Question:
   Which payment methods dominate marketplace transactions?

   Main payment method is defined as the payment record
   with the highest payment_value for each order.

   This is an analytical definition because some orders
   contain multiple payment records.
   ============================================================ */

WITH ranked_payments AS (

    SELECT
        order_id,
        payment_type,
        payment_value,
        payment_installments,

        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY
                payment_value DESC,
                payment_sequential
        ) AS rn

    FROM payments_clean
)

SELECT
    payment_type,

    COUNT(*) AS orders,

    ROUND(
        SUM(payment_value),
        2
    ) AS payment_value,

    ROUND(
        COUNT(*) /
        SUM(COUNT(*)) OVER () * 100,
        2
    ) AS order_share_percentage,

    ROUND(
        AVG(payment_value),
        2
    ) AS average_payment_value,

    ROUND(
        AVG(payment_installments),
        2
    ) AS average_installments

FROM ranked_payments

WHERE rn = 1

GROUP BY payment_type

ORDER BY payment_value DESC;


/* ============================================================
   13. STATE SALES PERFORMANCE
   Business Question:
   Which states combine high sales with different
   delivery/freight characteristics?
   ============================================================ */

SELECT
    c.customer_state AS state,

    ROUND(
        SUM(f.price),
        2
    ) AS revenue,

    COUNT(DISTINCT f.order_id) AS orders,

    ROUND(
        SUM(f.price) /
        COUNT(DISTINCT f.order_id),
        2
    ) AS average_order_value,

    ROUND(
        SUM(f.freight_value) /
        NULLIF(SUM(f.price), 0) * 100,
        2
    ) AS freight_percentage,

    ROUND(
        AVG(f.delivery_days),
        2
    ) AS average_delivery_days,

    ROUND(
        COUNT(
            DISTINCT
            CASE
                WHEN f.is_late = 1
                THEN f.order_id
            END
        )
        /
        COUNT(DISTINCT f.order_id) * 100,
        2
    ) AS late_rate_percentage

FROM fact_sales f

JOIN customers_clean c
    ON f.customer_id = c.customer_id

GROUP BY c.customer_state

HAVING COUNT(DISTINCT f.order_id) >= 500

ORDER BY revenue DESC;


/* ============================================================
   14. PRODUCT PRICE VS FREIGHT ANALYSIS
   Business Question:
   Which products generate high sales volume while
   carrying relatively high freight burden?
   ============================================================ */

WITH product_metrics AS (

    SELECT

        product_id,

        SUM(price) AS revenue,

        COUNT(*) AS items,

        AVG(price) AS average_price,

        AVG(freight_value) AS average_freight,

        SUM(freight_value) /
        NULLIF(SUM(price), 0) AS freight_ratio

    FROM fact_sales

    GROUP BY product_id
)

SELECT

    product_id,

    ROUND(revenue, 2) AS revenue,

    items,

    ROUND(average_price, 2) AS average_price,

    ROUND(average_freight, 2) AS average_freight,

    ROUND(
        freight_ratio * 100,
        2
    ) AS freight_percentage

FROM product_metrics

WHERE
    items >= 50
    AND freight_ratio >= 0.25

ORDER BY
    revenue DESC;


/* ============================================================
   15. FINAL BUSINESS PRIORITY ANALYSIS
   Business Question:
   Which categories deserve management attention based on
   revenue, delivery risk, logistics burden and satisfaction?

   This is a PRIORITIZATION framework,
   NOT a profitability calculation.

   Priority categories satisfy:
   - Revenue >= $200,000
   - Orders >= 1,000
   - Either elevated freight OR elevated late rate
   ============================================================ */

WITH category_sales AS (

    SELECT

        product_category_name_english AS category,

        SUM(price) AS revenue,

        COUNT(DISTINCT order_id) AS orders,

        COUNT(
            DISTINCT
            CASE
                WHEN is_late = 1
                THEN order_id
            END
        ) AS late_orders,

        SUM(freight_value) AS freight

    FROM fact_sales

    GROUP BY
        product_category_name_english
),

category_reviews AS (

    SELECT

        f.product_category_name_english AS category,

        AVG(r.review_score) AS average_review_score

    FROM fact_sales f

    JOIN reviews_clean r
        ON f.order_id = r.order_id

    GROUP BY
        f.product_category_name_english
)

SELECT

    s.category,

    ROUND(s.revenue, 2) AS revenue,

    s.orders,

    ROUND(
        s.late_orders /
        NULLIF(s.orders, 0) * 100,
        2
    ) AS late_rate_percentage,

    ROUND(
        s.freight /
        NULLIF(s.revenue, 0) * 100,
        2
    ) AS freight_percentage,

    ROUND(
        r.average_review_score,
        2
    ) AS average_review_score,

    CASE

        WHEN
            s.revenue >= 500000
            AND
            (
                s.late_orders /
                NULLIF(s.orders, 0) >= 0.08

                OR

                s.freight /
                NULLIF(s.revenue, 0) >= 0.20
            )
        THEN 'HIGH PRIORITY'

        WHEN
            s.revenue >= 200000
            AND
            (
                s.late_orders /
                NULLIF(s.orders, 0) >= 0.08

                OR

                s.freight /
                NULLIF(s.revenue, 0) >= 0.20
            )
        THEN 'MEDIUM PRIORITY'

        ELSE 'MONITOR'

    END AS business_priority

FROM category_sales s

LEFT JOIN category_reviews r
    ON s.category = r.category

WHERE
    s.revenue >= 200000
    AND s.orders >= 1000

ORDER BY

    CASE

        WHEN
            s.revenue >= 500000
            AND
            (
                s.late_orders /
                NULLIF(s.orders, 0) >= 0.08

                OR

                s.freight /
                NULLIF(s.revenue, 0) >= 0.20
            )
        THEN 1

        WHEN
            s.revenue >= 200000
            AND
            (
                s.late_orders /
                NULLIF(s.orders, 0) >= 0.08

                OR

                s.freight /
                NULLIF(s.revenue, 0) >= 0.20
            )
        THEN 2

        ELSE 3

    END,

    revenue DESC;


/* ============================================================
   END OF FINAL SQL PORTFOLIO
   ============================================================ */