import sqlite3
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_project import generate_data, train_churn_model, validate


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.customers, cls.monthly = generate_data(customer_count=160, months=12)

    def test_primary_keys_are_unique(self):
        self.assertFalse(self.customers["customer_id"].duplicated().any())
        self.assertFalse(self.monthly.duplicated(["customer_id", "month"]).any())

    def test_measures_are_in_valid_ranges(self):
        validate(self.customers, self.monthly)
        self.assertTrue(self.monthly["feature_adoption_rate"].between(0, 1).all())
        self.assertTrue(self.monthly["nps"].between(-100, 100).all())
        self.assertTrue((self.monthly["mrr"] >= 0).all())

    def test_churn_is_terminal(self):
        for _, group in self.monthly.sort_values("month").groupby("customer_id"):
            churn_positions = list(group.index[group["churn_flag"] == 1])
            if churn_positions:
                self.assertEqual(group.index[-1], churn_positions[-1])

    def test_model_outputs_probabilities_and_holdout_metrics(self):
        result = train_churn_model(self.customers, self.monthly)
        self.assertTrue(result.scores["churn_probability"].between(0, 1).all())
        self.assertGreater(result.metrics["test_rows"], 0)
        self.assertIn("roc_auc", result.metrics)
        self.assertTrue(set(result.scores["risk_band"]).issubset({"Low", "Medium", "High"}))


if __name__ == "__main__":
    unittest.main()

