# Power BI 3-Page Dashboard Architecture & DAX Specification

> **Important Note on `.pbix` Files:** Power BI Desktop `.pbix` files are proprietary binary archives that must be authored and saved inside Microsoft Power BI Desktop. Follow the exact data model, Power Query transformations, and copy-paste DAX measures below to build or refresh your 3-page report in under 15 minutes.

## 1. Data Source & Star Schema Model
Import `data/processed/olist_orders_master.csv` (order-level grain: 99,441 rows; 98,666 orders with items) alongside `data/raw/olist_sellers_dataset.csv` and a DAX `Calendar` table:
- **Fact Table:** `fact_orders` (`olist_orders_master.csv`)
- **Dimension Tables:**
  - `dim_calendar` (linked `1:*` on `Date` -> `fact_orders[order_purchase_date]`)
  - `dim_customers` (customer attributes & state)
  - `dim_sellers` (linked on `seller_id` -> `fact_orders[primary_seller_id]`)

## 2. Core DAX Measures (Copy-Paste Ready)

```dax
Total Item Revenue = SUM(fact_orders[total_price])

Total Freight Value = SUM(fact_orders[total_freight])

Total GMV = [Total Item Revenue] + [Total Freight Value]

Orders With Items =
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    NOT(ISBLANK(fact_orders[item_count]))
)

Total Active Sellers = DISTINCTCOUNT(dim_sellers[seller_id])

Average Order Value (AOV) =
DIVIDE([Total Item Revenue], [Orders With Items], 0)

Delivered Orders =
CALCULATE(
    DISTINCTCOUNT(fact_orders[order_id]),
    fact_orders[order_status] = "delivered",
    NOT(ISBLANK(fact_orders[order_delivered_customer_date])),
    NOT(ISBLANK(fact_orders[item_count]))
)

Late Delivered Orders =
CALCULATE(
    [Delivered Orders],
    fact_orders[is_late] = 1
)

Late Delivery Rate % =
DIVIDE([Late Delivered Orders], [Delivered Orders], 0)

On-Time Delivery Rate % = 1 - [Late Delivery Rate %]

Average Delivery Time (Days) =
CALCULATE(
    AVERAGE(fact_orders[actual_delivery_days]),
    fact_orders[order_status] = "delivered"
)

Average Review Score = AVERAGE(fact_orders[review_score])
```

## 3. Page-by-Page Visual Layout
### Page 1: Executive Overview
- **4 KPI Cards:** Total Item Revenue (`$13.59M`), Orders With Items (`98,666`), Total Active Sellers (`3,095`), Average Order Value (`$137.75`).
- **Line & Clustered Column Chart:** Monthly Revenue (`[Total Item Revenue]`) & Order Volume (`[Orders With Items]`) over `dim_calendar[Year-Month]`.
- **Filled Map / Bar Chart:** Revenue and Order Share by `customer_state`.

### Page 2: Sales and Seller Analysis
- **Horizontal Bar Chart:** Top 10 Product Categories (`primary_category`) by `[Total Item Revenue]`.
- **Matrix Table:** Top Sellers (`primary_seller_id`, `primary_seller_state`, `[Orders With Items]`, `[Total Item Revenue]`, `[Late Delivery Rate %]`).
- **Donut Chart:** Payment Method Breakdown (`primary_payment_type` vs. `[Orders With Items]`).

### Page 3: Delivery and Customer Analysis
- **4 KPI Cards:** On-Time Delivery Rate (`91.89%`), Late Delivery Rate (`8.11%`), Average Delivery Time (`12.56 Days`), Average Review Score (`4.09 ★`).
- **Column Chart:** Average Review Score by Delivery SLA Status (`4.29 ★` On-Time vs. `2.57 ★` Late).
- **Scatter / Bar Visual:** Interstate vs. Intrastate Late Delivery Rate (`is_interstate`) and Freight Ratio analysis.
