"""Unit tests for serialized pipeline loading and single/batch order prediction."""

import unittest
from src.prediction import predict_late_delivery


class TestPrediction(unittest.TestCase):
    def test_predict_late_delivery_schema_and_bounds(self):
        sample_orders = [
            {
                "order_purchase_timestamp": "2026-11-18 10:15:00",
                "order_approved_at": "2026-11-18 10:30:00",
                "order_estimated_delivery_date": "2026-11-25 00:00:00",
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
            }
        ]
        preds = predict_late_delivery(sample_orders, model_dir="models/saved_models")
        self.assertEqual(len(preds), 1)
        res = preds[0]
        self.assertIn("late_probability", res)
        self.assertIn("predicted_late", res)
        self.assertIn("risk_tier", res)
        self.assertTrue(0.0 <= res["late_probability"] <= 1.0)
        self.assertIn(res["predicted_late"], [0, 1])
        self.assertIn(res["risk_tier"], ["LOW", "MEDIUM", "HIGH"])


if __name__ == "__main__":
    unittest.main()
