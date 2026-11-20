# Olist Dataset Guide & Local Setup

## Why Raw CSVs Are Not Committed to GitHub
To keep the repository lightweight and adhere to GitHub best practices, the 9 raw Olist CSV datasets (~120 MB total) and generated processed CSVs are excluded via `.gitignore`.

## How to Obtain and Place the Dataset Locally
1. Download the **Brazilian E-Commerce Public Dataset by Olist** from Kaggle (`olistbr/brazilian-ecommerce`) or use your local archive.
2. Place all **9 CSV files** directly inside `data/raw/`:
   - `olist_customers_dataset.csv` (99,441 rows)
   - `olist_geolocation_dataset.csv` (1,000,163 rows)
   - `olist_order_items_dataset.csv` (112,650 rows)
   - `olist_order_payments_dataset.csv` (103,886 rows)
   - `olist_order_reviews_dataset.csv` (99,224 rows)
   - `olist_orders_dataset.csv` (99,441 rows)
   - `olist_products_dataset.csv` (32,951 rows)
   - `olist_sellers_dataset.csv` (3,095 rows)
   - `product_category_name_translation.csv` (71 rows)
3. Run the preprocessing and feature engineering pipeline from the project root:
   ```bash
   python -c "from src.data.load_data import load_raw_datasets; from src.data.preprocess import build_master_order_dataset, save_processed_datasets; save_processed_datasets(build_master_order_dataset(load_raw_datasets('data/raw')))"
   ```
