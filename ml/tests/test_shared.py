import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np

from ml.shared.evaluate import artifact_size, evaluate, measure_call, score_predictions
from ml.shared.protocol import fit_training_text, load_contract, majority_category

class SharedProtocolTests(unittest.TestCase):
    def test_contract_coverage(self):
        splits, labels = load_contract()
        self.assertEqual({s: len(r) for s, r in splits.items()}, {"train": 375, "validation": 80, "test": 84})
        self.assertEqual(len(labels), 13)

    def test_holdout_cannot_change_vocabulary_or_idf(self):
        vectorizer, _ = fit_training_text([{"description": "grocery market"}, {"description": "rent payment"}])
        vocabulary, idf = vectorizer.vocabulary_.copy(), vectorizer.idf_.copy()
        vectorizer.transform(["uniquetestword grocery", "differentholdoutword rent"])
        self.assertEqual(vectorizer.vocabulary_, vocabulary)
        np.testing.assert_array_equal(vectorizer.idf_, idf)
        self.assertNotIn("uniquetestword", vocabulary)
        self.assertNotIn("differentholdoutword", vocabulary)
        self.assertIn("grocery market", vocabulary)

    def test_vectorizer_roundtrip(self):
        vectorizer, _ = fit_training_text([{"description": "grocery market"}, {"description": "rent payment"}])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "local_test_vectorizer.joblib"
            joblib.dump(vectorizer, path)
            loaded = joblib.load(path)
            np.testing.assert_array_equal(loaded.transform(["market rent"]).toarray(), vectorizer.transform(["market rent"]).toarray())
            self.assertGreater(artifact_size(path), 0)

    def test_hand_calculated_metrics_and_reordered_ids(self):
        expected = [{"transaction_id": str(i), "category": c} for i, c in enumerate(["A", "A", "A", "B"])]
        predictions = [{"transaction_id": str(i), "category": c} for i, c in enumerate(["A", "A", "B", "B"])][::-1]
        report = score_predictions(expected, predictions, {"A": 0, "B": 1})
        self.assertEqual(report["confusion_matrix"], [[2, 1], [0, 1]])
        self.assertEqual(report["accuracy"], 0.75)
        self.assertAlmostEqual(report["macro_f1"], 11 / 15)
        self.assertAlmostEqual(report["weighted_f1"], 23 / 30)
        self.assertAlmostEqual(report["worst_class_recall"], 2 / 3)
        self.assertEqual(report["per_class"]["A"]["support"], 3)

    def test_invalid_predictions_rejected(self):
        expected = [{"transaction_id": "a", "category": "A"}, {"transaction_id": "b", "category": "B"}]
        for predictions in [expected[:1], expected + expected[:1],
                [{"transaction_id": "a", "category": "unknown"}, expected[1]],
                [{"transaction_id": "extra", "category": "A"}, expected[1]]]:
            with self.subTest(predictions=predictions), self.assertRaises(ValueError):
                score_predictions(expected, predictions, {"A": 0, "B": 1})

    def test_unpredicted_category_visible(self):
        expected = [{"transaction_id": "a", "category": "A"}, {"transaction_id": "b", "category": "B"}]
        guesses = [dict(row, category="A") for row in expected]
        report = score_predictions(expected, guesses, {"A": 0, "B": 1})
        self.assertEqual(report["per_class"]["B"]["precision"], 0)
        self.assertEqual(report["unpredicted_labels"], ["B"])

    def test_test_evaluation_blocked_by_default(self):
        with self.assertRaises(PermissionError):
            evaluate([], split="test")
        with self.assertRaises(ValueError):
            evaluate([], split="train")

    def test_majority_uses_only_supplied_training_rows(self):
        rows = [{"category": "B"}, {"category": "A"}, {"category": "B"}]
        self.assertEqual(majority_category(rows, {"A": 0, "B": 1}), "B")
        self.assertEqual(majority_category(rows[:2], {"A": 0, "B": 1}), "A")

    def test_measurement_and_exception_cleanup(self):
        value, stats = measure_call(lambda: bytearray(10000))
        self.assertEqual(len(value), 10000)
        self.assertGreater(stats["python_traced_peak_bytes"], 0)
        with self.assertRaises(ZeroDivisionError):
            measure_call(lambda: 1 / 0)
        self.assertEqual(measure_call(lambda: 7)[0], 7)

if __name__ == "__main__":
    unittest.main()
