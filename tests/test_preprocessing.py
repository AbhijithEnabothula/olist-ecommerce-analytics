"""Unit tests for data cleaning and multi-table aggregation without row explosion."""

import unittest
import pandas as pd
from src.data.preprocess import clean_geolocation


class TestPreprocessing(unittest.TestCase):
    def test_clean_geolocation_deduplicates_zip(self):
        sample_geo = pd.DataFrame({
            "geolocation_zip_code_prefix": [1001, 1001, 1001, 2002],
            "geolocation_lat": [-23.5, -23.6, -23.4, -22.9],
            "geolocation_lng": [-46.6, -46.7, -46.5, -43.2],
        })
        cleaned = clean_geolocation(sample_geo)
        self.assertEqual(len(cleaned), 2)
        self.assertTrue(cleaned["geolocation_zip_code_prefix"].is_unique)

    def test_master_dataset_uniqueness_and_metrics(self):
        master = pd.read_csv("data/processed/olist_orders_master.csv")
        self.assertEqual(len(master), 99441)
        self.assertTrue(master["order_id"].is_unique)
        valid_items = master[master["item_count"].notna()]
        self.assertEqual(len(valid_items), 98666)
        self.assertAlmostEqual(float(valid_items["total_price"].sum()), 13591643.70, places=2)


if __name__ == "__main__":
    unittest.main()
