# Executive Business Insights & Recommendations

## 1. Verified Descriptive & Financial Baseline
- **Scale & Revenue:** Across **99,441** total orders, **98,666** contain line items fulfilled by **3,095** unique sellers, generating **$13,591,643.70** in item revenue (**$15,843,553.24** total GMV including freight) and an **Average Order Value (AOV) of $137.75**.
- **Category Concentration:** Top 5 categories (`health_beauty`, `watches_gifts`, `bed_bath_table`, `sports_leisure`, `computers_accessories`) drive **39.8%** of total item revenue.
- **Payment Preferences:** Credit cards dominate checkout (`75.3%` of orders), followed by Boleto (`19.8%`), vouchers (`2.9%`), and debit cards (`1.5%`).

## 2. Logistics & Customer Satisfaction Findings
- **Delivery Cycle & SLA Breaches:** Among **96,470** delivered orders with complete timestamps and line items, the average delivery duration is **12.56 days**, and **8.11%** (**7,826 orders**) arrive after the estimated delivery date.
- **Severe Review Score Penalty:** Orders delivered on or before the estimated deadline achieve an average review score of **4.29 ★** (median **5.0 ★**), whereas late deliveries plummet to **2.57 ★** (median **2.0 ★**) — a **1.72-star drop** that directly erodes repeat buyer retention.
- **Geographic & Temporal Bottlenecks:**
  - **São Paulo (SP)** accounts for **41.9%** of delivered orders with a low **5.89%** late rate due to short intrastate transit (**7.9 days** average).
  - Long-haul shipments to **Rio de Janeiro (RJ)** and **Bahia (BA)** experience **13.47%** and **14.04%** late delivery rates (**14.8–19.3 days** average transit).
  - Network-wide late rates spiked during **Black Friday (Nov 2017: 14.3%)** and the **Correios postal strike (Feb–Mar 2018: 16.0%–21.4%)**.

## 3. Machine Learning Insights & Operational Recommendations
1. **Dynamic Checkout SLA Buffering:** `estimated_delivery_days` is the single strongest pre-shipment predictor of late delivery (`0.0870` PR-AUC permutation importance). Tightening under-padded SLA estimates on interstate routes (`SP -> RJ`, `SP -> BA`) by **+3 to +4 business days** during peak months reduces SLA breaches without increasing physical transit cost.
2. **Multi-Seller Order Split Alerts:** Orders fulfilled by multiple sellers (`unique_seller_count > 1` / `is_multi_seller`) carry elevated partial-delay risk. Trigger automated split-shipment tracking notifications at order approval.
3. **Pre-Shipment Priority Routing:** Deploy `src/prediction.py` (`Logistic Regression (Balanced)`, **0.7615 chronological Test ROC-AUC**, **0.1324 Test PR-AUC** vs. 0.0529 baseline) at `order_approved_at` to flag the top risk decile of orders (probability `>= 0.5755`) for expedited seller dispatch reminders and priority carrier handoff.
