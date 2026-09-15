# Olist E-Commerce Business Insights Report

## 1. Executive Summary

This project analyzes the Olist Brazilian E-Commerce Public Dataset to understand marketplace sales performance, category performance, seller contribution, logistics, customer satisfaction, payments, geography, and product-level freight behavior.

The analysis covers approximately 100K marketplace orders and combines Python/Pandas, MySQL/SQL, and Power BI to transform raw transactional data into business insights.

### Key Results

| KPI | Result |
|---|---:|
| Item Revenue | $13.59M |
| Orders with Sales Items | 98,666 |
| Average Order Value | $137.75 |
| Order Items | 112,650 |
| Sellers | 3,095 |
| Products | 32,951 |
| Average Delivery Time | 12.56 days |
| Late Order Rate | 7.93% |
| Average Review Score | 4.09 / 5 |

The analysis identified three major business themes:

1. Revenue is driven by a combination of high-performing categories and a relatively concentrated group of sellers.
2. Logistics performance is strongly associated with customer satisfaction.
3. Product size and weight have a meaningful relationship with freight costs.

---

# 2. Business Objective

The objective of this project is to analyze the Olist marketplace and answer important business questions related to:

- Revenue growth
- Order volume
- Average order value
- Category performance
- Seller performance
- Product performance
- Delivery reliability
- Customer satisfaction
- Payment behavior
- Geographic performance
- Freight costs

The ultimate goal is to convert raw marketplace data into actionable recommendations for improving revenue, logistics, seller performance, and customer experience.

---

# 3. Dataset Overview

The project uses the Olist Brazilian E-Commerce Public Dataset.

The raw data consists of nine datasets:

| Dataset | Purpose |
|---|---|
| Customers | Customer information and location |
| Orders | Order lifecycle and delivery information |
| Order Items | Products, sellers, prices and freight |
| Products | Product attributes |
| Sellers | Seller information |
| Payments | Payment methods and installments |
| Reviews | Customer review scores and comments |
| Geolocation | ZIP-code geographic information |
| Category Translation | Portuguese-to-English category mapping |

The datasets have different levels of detail, so understanding table grain and relationships was an important part of the analysis.

---

# 4. Data Preparation

Python and Pandas were used for data ingestion, auditing, cleaning, and feature engineering.

## 4.1 Data Audit

The following checks were performed:

- Dataset dimensions
- Data types
- Missing values
- Duplicate records
- Unique identifiers
- Negative numeric values
- Zero values
- Date consistency
- Categorical distributions
- Relationship consistency

---

## 4.2 Missing Values

Missing values were investigated rather than automatically deleted.

For example, several product records had missing descriptive attributes and category information.

The affected products were still associated with order-item records, meaning deleting them could remove valid sales information.

Missing product categories were therefore assigned an `unknown` category for analysis.

---

## 4.3 Duplicate Records

The geolocation dataset contained a large number of exact duplicate rows.

These were retained because repeated ZIP-code/location combinations can represent legitimate geographic mappings and should not automatically be interpreted as erroneous transactional duplicates.

---

## 4.4 Date Validation

Order timestamps were converted to datetime format.

Important chronological checks included:

- Purchase before approval
- Purchase before delivery
- Approval before carrier delivery
- Carrier delivery before customer delivery
- Customer delivery versus estimated delivery

Delivery delays were treated as business events rather than simply deleting the affected records.

---

# 5. Data Modeling

One of the most important technical decisions in the project was identifying the correct analytical grain.

## 5.1 Different Table Grains

For example:

```text
Orders
1 row = 1 order

Order Items
1 row = 1 order item

Payments
1 row = 1 payment transaction

Reviews
1 row = 1 review