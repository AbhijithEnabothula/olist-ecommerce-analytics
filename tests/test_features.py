"""Unit tests for leakage prevention and feature engineering calculations."""

import unittest
import pandas as pd
from src.features.build_features import (
    ALL_FEATURE_COLUMNS,
    FORBIDDEN_LEAKAGE_COLUMNS,
    get_feature_matrix_and_target,
    haversine_distance_km,
)


class TestFeatures(unittest.TestCase):
    def test_zero_post_delivery_leakage(self):
        overlap = set(ALL_FEATURE_COLUMNS).intersection(FORBIDDEN_LEAKAGE_COLUMNS)
        self.assertEqual(len(overlap), 0, f"Forbidden leakage columns present: {overlap}")

    def test_haversine_zero_and_positive_distance(self):
        d_zero = haversine_distance_km(
            pd.Series([-23.55]), pd.Series([-46.63]), pd.Series([-23.55]), pd.Series([-46.63])
        )
        self.assertAlmostEqual(float(d_zero.iloc[0]), 0.0, places=4)
        d_sp_rj = haversine_distance_km(
            pd.Series([-23.5505]), pd.Series([-46.6333]), pd.Series([-22.9068]), pd.Series([-43.1729])
        )
        self.assertTrue(340.0 <= float(d_sp_rj.iloc[0]) <= 380.0)

    def test_feature_matrix_shape(self):
        featured = pd.read_csv("data/processed/olist_ml_features.csv")
        X, y = get_feature_matrix_and_target(featured)
        self.assertEqual(len(X), 96456)
        self.assertEqual(X.shape[1], len(ALL_FEATURE_COLUMNS))
        self.assertEqual(set(y.unique()), {0, 1})


if __name__ == "__main__":
    unittest.main()
