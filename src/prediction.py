"""Standalone inference script for predicting late delivery risk on new approved orders."""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List
import joblib
import numpy as np
import pandas as pd

from src.features.build_features import ALL_FEATURE_COLUMNS, haversine_distance_km


def prepare_single_order_features(order_input: Dict[str, Any]) -> pd.DataFrame:
    """Transform a raw pre-shipment order payload into the exact model feature schema."""
    purchase_ts = pd.to_datetime(order_input["order_purchase_timestamp"])
    approved_ts = pd.to_datetime(order_input.get("order_approved_at", purchase_ts))
    estimated_ts = pd.to_datetime(order_input["order_estimated_delivery_date"])
    shipping_limit_ts = pd.to_datetime(order_input.get("shipping_limit_date_min", approved_ts))

    month = int(purchase_ts.month)
    dow = int(purchase_ts.dayofweek)
    hour = int(purchase_ts.hour)

    item_count = max(int(order_input.get("item_count", 1)), 1)
    unique_seller_count = max(int(order_input.get("unique_seller_count", 1)), 1)
    total_price = float(order_input["total_price"])
    total_freight = float(order_input["total_freight"])

    if "seller_customer_distance_km" in order_input and order_input["seller_customer_distance_km"] is not None:
        dist_km = float(order_input["seller_customer_distance_km"])
    else:
        dist_km = float(
            haversine_distance_km(
                pd.Series([order_input["primary_seller_lat"]]),
                pd.Series([order_input["primary_seller_lng"]]),
                pd.Series([order_input["customer_lat"]]),
                pd.Series([order_input["customer_lng"]]),
            ).iloc[0]
        )

    customer_state = str(order_input.get("customer_state", "unknown"))
    seller_state = str(order_input.get("primary_seller_state", "unknown"))

    row = {
        "month_sin": float(np.sin(2.0 * np.pi * month / 12.0)),
        "month_cos": float(np.cos(2.0 * np.pi * month / 12.0)),
        "dow_sin": float(np.sin(2.0 * np.pi * dow / 7.0)),
        "dow_cos": float(np.cos(2.0 * np.pi * dow / 7.0)),
        "order_purchase_hour": hour,
        "is_weekend_purchase": int(dow >= 5),
        "approval_lag_hours": max((approved_ts - purchase_ts).total_seconds() / 3600.0, 0.0),
        "estimated_delivery_days": max((estimated_ts - purchase_ts).total_seconds() / 86400.0, 0.0),
        "shipping_limit_days": max((shipping_limit_ts - approved_ts).total_seconds() / 86400.0, 0.0),
        "item_count": item_count,
        "unique_product_count": int(order_input.get("unique_product_count", item_count)),
        "unique_seller_count": unique_seller_count,
        "is_multi_seller": int(unique_seller_count > 1),
        "total_price": total_price,
        "total_freight": total_freight,
        "freight_ratio": (total_freight / total_price) if total_price > 0 else 0.0,
        "price_per_item": total_price / item_count,
        "total_weight_g": float(order_input.get("total_weight_g", 500.0)),
        "max_item_weight_g": float(
            order_input.get("max_item_weight_g", order_input.get("total_weight_g", 500.0))
        ),
        "total_volume_cm3": float(order_input.get("total_volume_cm3", 3000.0)),
        "seller_customer_distance_km": dist_km,
        "freight_per_km": total_freight / (dist_km + 1.0),
        "is_interstate": int(customer_state != seller_state),
        "payment_count": int(order_input.get("payment_count", 1)),
        "max_installments": int(order_input.get("max_installments", 1)),
        "total_payment_value": float(
            order_input.get("total_payment_value", total_price + total_freight)
        ),
        "customer_state": customer_state,
        "primary_seller_state": seller_state,
        "primary_category": str(order_input.get("primary_category", "other")),
        "primary_payment_type": str(order_input.get("primary_payment_type", "credit_card")),
    }
    return pd.DataFrame([row])[ALL_FEATURE_COLUMNS]


def predict_late_delivery(
    orders: List[Dict[str, Any]],
    model_dir: str | Path = "models/saved_models",
) -> List[Dict[str, Any]]:
    """Predict late delivery probability, risk tier, and binary alert for new orders."""
    base_dir = Path(model_dir)
    pipeline = joblib.load(base_dir / "late_delivery_pipeline.joblib")
    with open(base_dir / "model_metadata.json", "r") as f:
        metadata = json.load(f)

    threshold = float(metadata["optimal_threshold"])
    feature_df = pd.concat([prepare_single_order_features(o) for o in orders], ignore_index=True)
    probs = pipeline.predict_proba(feature_df)[:, 1]

    predictions = []
    for idx, prob in enumerate(probs):
        prob_val = round(float(prob), 4)
        if prob_val >= threshold:
            risk_tier = "HIGH"
        elif prob_val >= (threshold * 0.70):
            risk_tier = "MEDIUM"
        else:
            risk_tier = "LOW"

        predictions.append(
            {
                "order_index": idx,
                "late_probability": prob_val,
                "decision_threshold": threshold,
                "predicted_late": int(prob_val >= threshold),
                "risk_tier": risk_tier,
            }
        )
    return predictions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score new orders for late delivery risk.")
    parser.add_argument("--model-dir", default="models/saved_models", help="Directory with saved joblib model.")
    args = parser.parse_args()

    sample_orders = [
        {
            "order_purchase_timestamp": "2026-11-18 10:15:00",
            "order_approved_at": "2026-11-18 10:30:00",
            "order_estimated_delivery_date": "2026-11-26 00:00:00",
            "shipping_limit_date_min": "2026-11-21 10:30:00",
            "item_count": 2,
            "unique_seller_count": 2,
            "total_price": 240.0,
            "total_freight": 58.5,
            "total_weight_g": 4200.0,
            "total_volume_cm3": 18500.0,
            "seller_customer_distance_km": 1850.0,
            "customer_state": "BA",
            "primary_seller_state": "SP",
            "primary_category": "furniture_decor",
            "primary_payment_type": "credit_card",
            "max_installments": 4,
        },
        {
            "order_purchase_timestamp": "2026-11-18 14:00:00",
            "order_approved_at": "2026-11-18 14:10:00",
            "order_estimated_delivery_date": "2026-12-10 00:00:00",
            "shipping_limit_date_min": "2026-11-23 14:10:00",
            "item_count": 1,
            "unique_seller_count": 1,
            "total_price": 89.9,
            "total_freight": 12.4,
            "total_weight_g": 450.0,
            "total_volume_cm3": 1600.0,
            "seller_customer_distance_km": 45.0,
            "customer_state": "SP",
            "primary_seller_state": "SP",
            "primary_category": "health_beauty",
            "primary_payment_type": "credit_card",
            "max_installments": 1,
        },
    ]
    print(json.dumps(predict_late_delivery(sample_orders, model_dir=args.model_dir), indent=2))
