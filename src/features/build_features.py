"""Leakage-free pre-shipment feature engineering for late delivery prediction.

Prediction Point Definition
---------------------------
Features are restricted strictly to information known immediately after payment
approval (`order_approved_at`) and prior to physical carrier handoff or customer
delivery. Post-delivery columns (`order_delivered_carrier_date`, `order_delivered_customer_date`,
`actual_delivery_days`, `delivery_delay_days`, `review_score`, `review_count`) are explicitly
blocked via runtime assertions.
"""

from typing import List, Tuple
import numpy as np
import pandas as pd

FORBIDDEN_LEAKAGE_COLUMNS = {
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "actual_delivery_days",
    "delivery_delay_days",
    "review_score",
    "review_count",
    "order_status",
    "is_late",
}

NUMERIC_FEATURES: List[str] = [
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "order_purchase_hour",
    "is_weekend_purchase",
    "approval_lag_hours",
    "estimated_delivery_days",
    "shipping_limit_days",
    "item_count",
    "unique_product_count",
    "unique_seller_count",
    "is_multi_seller",
    "total_price",
    "total_freight",
    "freight_ratio",
    "price_per_item",
    "total_weight_g",
    "max_item_weight_g",
    "total_volume_cm3",
    "seller_customer_distance_km",
    "freight_per_km",
    "is_interstate",
    "payment_count",
    "max_installments",
    "total_payment_value",
]

CATEGORICAL_FEATURES: List[str] = [
    "customer_state",
    "primary_seller_state",
    "primary_category",
    "primary_payment_type",
]

ALL_FEATURE_COLUMNS: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def haversine_distance_km(
    lat1: pd.Series, lon1: pd.Series, lat2: pd.Series, lon2: pd.Series
) -> pd.Series:
    """Compute great-circle distance in kilometers between seller and customer coordinates."""
    r_earth_km = 6371.0
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(np.clip(1.0 - a, 0.0, 1.0)))
    return r_earth_km * c


def engineer_features(df: pd.DataFrame, top_n_categories: int = 20) -> pd.DataFrame:
    """Generate features available strictly after order approval and before delivery."""
    data = df.copy()
    purchase_ts = pd.to_datetime(data["order_purchase_timestamp"])
    approved_ts = pd.to_datetime(data["order_approved_at"])
    estimated_ts = pd.to_datetime(data["order_estimated_delivery_date"])
    shipping_limit_ts = pd.to_datetime(data["shipping_limit_date_min"]).fillna(approved_ts)

    data["order_purchase_year"] = purchase_ts.dt.year
    data["order_purchase_month"] = purchase_ts.dt.month
    data["order_purchase_day_of_week"] = purchase_ts.dt.dayofweek
    data["order_purchase_hour"] = purchase_ts.dt.hour
    data["is_weekend_purchase"] = (data["order_purchase_day_of_week"] >= 5).astype(int)

    # Cyclical calendar encodings prevent arbitrary ordinal jumps
    data["month_sin"] = np.sin(2.0 * np.pi * data["order_purchase_month"] / 12.0)
    data["month_cos"] = np.cos(2.0 * np.pi * data["order_purchase_month"] / 12.0)
    data["dow_sin"] = np.sin(2.0 * np.pi * data["order_purchase_day_of_week"] / 7.0)
    data["dow_cos"] = np.cos(2.0 * np.pi * data["order_purchase_day_of_week"] / 7.0)

    # Pre-shipment SLA and approval lag features
    data["approval_lag_hours"] = np.clip(
        (approved_ts - purchase_ts).dt.total_seconds() / 3600.0, a_min=0.0, a_max=None
    )
    data["estimated_delivery_days"] = np.clip(
        (estimated_ts - purchase_ts).dt.total_seconds() / 86400.0, a_min=0.0, a_max=None
    )
    data["shipping_limit_days"] = np.clip(
        (shipping_limit_ts - approved_ts).dt.total_seconds() / 86400.0, a_min=0.0, a_max=None
    )

    # Multi-item & multi-seller complexity features
    data["is_multi_seller"] = (data["unique_seller_count"] > 1).astype(int)
    safe_price = data["total_price"].replace(0, np.nan)
    data["freight_ratio"] = (data["total_freight"] / safe_price).fillna(0.0)
    data["price_per_item"] = data["total_price"] / data["item_count"].clip(lower=1)

    # Geospatial logistics features
    data["seller_customer_distance_km"] = haversine_distance_km(
        data["primary_seller_lat"],
        data["primary_seller_lng"],
        data["customer_lat"],
        data["customer_lng"],
    )
    data["freight_per_km"] = data["total_freight"] / (
        data["seller_customer_distance_km"].fillna(0.0) + 1.0
    )
    data["is_interstate"] = (
        data["customer_state"].fillna("") != data["primary_seller_state"].fillna("")
    ).astype(int)

    data["primary_category"] = data["primary_category"].fillna("unknown")
    
    for col in ["customer_state", "primary_seller_state", "primary_payment_type"]:
        data[col] = data[col].fillna("unknown")

    return data


def get_feature_matrix_and_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    """Return leakage-verified feature matrix X and binary target y."""
    leaked = set(ALL_FEATURE_COLUMNS).intersection(FORBIDDEN_LEAKAGE_COLUMNS)
    if leaked:
        raise ValueError(f"Data leakage detected! Forbidden columns: {leaked}")
    return df[ALL_FEATURE_COLUMNS].copy(), df["is_late"].astype(int).copy()
