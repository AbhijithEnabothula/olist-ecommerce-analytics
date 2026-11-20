"""Data loading and schema validation utilities for the Olist E-Commerce dataset."""

from pathlib import Path
from typing import Dict
import pandas as pd

EXPECTED_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "geolocation": "olist_geolocation_dataset.csv",
}


def load_raw_datasets(raw_dir: str | Path = "data/raw") -> Dict[str, pd.DataFrame]:
    """Load all nine raw Olist CSV datasets with file existence validation."""
    raw_path = Path(raw_dir)
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw data directory not found: {raw_path.resolve()}. "
            "Place the 9 raw Olist CSV files in data/raw/ (see data/README.md)."
        )

    missing_files = [
        fname for fname in EXPECTED_FILES.values() if not (raw_path / fname).exists()
    ]
    if missing_files:
        raise FileNotFoundError(
            f"Missing required raw dataset file(s) in {raw_path.resolve()}: {missing_files}"
        )

    return {key: pd.read_csv(raw_path / fname) for key, fname in EXPECTED_FILES.items()}
