"""Data cleaning and order-level multi-table integration without row multiplication."""

from pathlib import Path
from typing import Dict
import numpy as np
import pandas as pd


def clean_geolocation(geo_df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate geolocation rows to median (lat, lng) per zip prefix."""
    return (
        geo_df.dropna(subset=["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng"])
        .groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(lat=("geolocation_lat", "median"), lng=("geolocation_lng", "median"))
    )


def clean_products(products_df: pd.DataFrame, translation_df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names, translate Portuguese categories, and impute dimensions."""
    prod = products_df.rename(
        columns={
            "product_name_lenght": "product_name_length",
            "product_description_lenght": "product_description_length",
        }
    ).copy()
    prod = prod.merge(translation_df, on="product_category_name", how="left")
    prod["product_category_english"] = (
        prod["product_category_name_english"]
        .fillna(prod["product_category_name"])
        .fillna("unknown")
    )

    for col in ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]:
        prod[col] = prod[col].fillna(prod[col].median())

    prod["product_volume_cm3"] = (
        prod["product_length_cm"] * prod["product_height_cm"] * prod["product_width_cm"]
    )
    return prod


def aggregate_order_items(
    items_df: pd.DataFrame,
    products_clean: pd.DataFrame,
    sellers_df: pd.DataFrame,
    geo_clean: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate line-item rows to strictly one row per `order_id`."""
    items_enriched = (
        items_df.merge(
            products_clean[
                ["product_id", "product_category_english", "product_weight_g", "product_volume_cm3"]
            ],
            on="product_id",
            how="left",
        )
        .merge(
            sellers_df[["seller_id", "seller_zip_code_prefix", "seller_state"]],
            on="seller_id",
            how="left",
        )
        .merge(
            geo_clean.rename(
                columns={
                    "geolocation_zip_code_prefix": "seller_zip_code_prefix",
                    "lat": "seller_lat",
                    "lng": "seller_lng",
                }
            ),
            on="seller_zip_code_prefix",
            how="left",
        )
    )
    items_enriched["shipping_limit_date"] = pd.to_datetime(items_enriched["shipping_limit_date"])

    # Primary item per order = highest priced item (tie-broken by order_item_id)
    primary_items = (
        items_enriched.sort_values(
            by=["order_id", "price", "order_item_id"], ascending=[True, False, True]
        )
        .drop_duplicates(subset=["order_id"], keep="first")[
            [
                "order_id",
                "product_category_english",
                "seller_id",
                "seller_state",
                "seller_lat",
                "seller_lng",
            ]
        ]
        .rename(
            columns={
                "product_category_english": "primary_category",
                "seller_id": "primary_seller_id",
                "seller_state": "primary_seller_state",
                "seller_lat": "primary_seller_lat",
                "seller_lng": "primary_seller_lng",
            }
        )
    )

    agg_items = items_enriched.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        unique_product_count=("product_id", "nunique"),
        unique_seller_count=("seller_id", "nunique"),
        total_price=("price", "sum"),
        total_freight=("freight_value", "sum"),
        total_weight_g=("product_weight_g", "sum"),
        max_item_weight_g=("product_weight_g", "max"),
        total_volume_cm3=("product_volume_cm3", "sum"),
        shipping_limit_date_min=("shipping_limit_date", "min"),
    )

    order_items_agg = agg_items.merge(primary_items, on="order_id", how="left")
    assert order_items_agg["order_id"].is_unique, "Duplicate order_id in aggregated items!"
    return order_items_agg


def aggregate_payments(payments_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate payment rows to strictly one row per `order_id`."""
    primary_pay = (
        payments_df.sort_values(
            by=["order_id", "payment_value", "payment_sequential"], ascending=[True, False, True]
        )
        .drop_duplicates(subset=["order_id"], keep="first")[["order_id", "payment_type"]]
        .rename(columns={"payment_type": "primary_payment_type"})
    )
    agg_pay = payments_df.groupby("order_id", as_index=False).agg(
        payment_count=("payment_sequential", "count"),
        max_installments=("payment_installments", "max"),
        total_payment_value=("payment_value", "sum"),
    )
    payments_agg = agg_pay.merge(primary_pay, on="order_id", how="left")
    assert payments_agg["order_id"].is_unique, "Duplicate order_id in aggregated payments!"
    return payments_agg


def aggregate_reviews(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate review records to one row per `order_id` (for EDA/SQL only)."""
    rev_agg = reviews_df.groupby("order_id", as_index=False).agg(
        review_score=("review_score", "mean"),
        review_count=("review_id", "count"),
    )
    assert rev_agg["order_id"].is_unique, "Duplicate order_id in aggregated reviews!"
    return rev_agg


def build_master_order_dataset(datasets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Integrate all 9 Olist datasets into a clean, validated order-level table."""
    orders = datasets["orders"].copy()
    for col in [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        orders[col] = pd.to_datetime(orders[col])

    geo_clean = clean_geolocation(datasets["geolocation"])
    products_clean = clean_products(datasets["products"], datasets["category_translation"])

    customers_geo = datasets["customers"].merge(
        geo_clean.rename(
            columns={
                "geolocation_zip_code_prefix": "customer_zip_code_prefix",
                "lat": "customer_lat",
                "lng": "customer_lng",
            }
        ),
        on="customer_zip_code_prefix",
        how="left",
    )

    items_agg = aggregate_order_items(
        datasets["order_items"], products_clean, datasets["sellers"], geo_clean
    )
    payments_agg = aggregate_payments(datasets["order_payments"])
    reviews_agg = aggregate_reviews(datasets["order_reviews"])

    master = (
        orders.merge(customers_geo, on="customer_id", how="left")
        .merge(items_agg, on="order_id", how="left")
        .merge(payments_agg, on="order_id", how="left")
        .merge(reviews_agg, on="order_id", how="left")
    )

    assert len(master) == len(orders), f"Row count mismatch: {len(master)} vs {len(orders)}"
    assert master["order_id"].is_unique, "Duplicate order_id in master dataset!"

    master["actual_delivery_days"] = (
        master["order_delivered_customer_date"] - master["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400.0
    master["delivery_delay_days"] = (
        master["order_delivered_customer_date"] - master["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400.0
    master["is_late"] = np.where(
        master["order_delivered_customer_date"].notna()
        & master["order_estimated_delivery_date"].notna(),
        (master["order_delivered_customer_date"] > master["order_estimated_delivery_date"]).astype(int),
        np.nan,
    )
    return master


def save_processed_datasets(master_df: pd.DataFrame, processed_dir: str | Path = "data/processed") -> None:
    """Save master order dataset and delivered-order modeling dataset."""
    out_path = Path(processed_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    master_df.to_csv(out_path / "olist_orders_master.csv", index=False)

    modeling_df = master_df[
        (master_df["order_status"] == "delivered")
        & master_df["order_delivered_customer_date"].notna()
        & master_df["order_estimated_delivery_date"].notna()
        & master_df["order_approved_at"].notna()
        & master_df["item_count"].notna()
    ].copy()
    modeling_df.to_csv(out_path / "olist_delivered_orders.csv", index=False)
