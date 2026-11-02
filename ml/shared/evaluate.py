"""Evaluate caller-supplied predictions; this module never trains a model."""
from pathlib import Path
from time import perf_counter
import tracemalloc

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from .protocol import load_contract

def score_predictions(expected_rows, predictions, labels):
    expected = {r["transaction_id"]: r["category"] for r in expected_rows}
    predicted = {r["transaction_id"]: r["category"] for r in predictions}
    if not expected or len(expected) != len(expected_rows) or len(predicted) != len(predictions):
        raise ValueError("Empty evaluation or duplicate transaction IDs")
    if set(expected) != set(predicted):
        raise ValueError("Predictions must cover exactly the requested split")
    order = sorted(labels, key=labels.get)
    if (set(expected.values()) | set(predicted.values())) - set(order):
        raise ValueError("Unknown prediction or reference category")
    truth = [expected[key] for key in expected]
    guesses = [predicted[key] for key in expected]
    precision, recall, f1, support = precision_recall_fscore_support(
        truth, guesses, labels=order, zero_division=0)
    return {"evidence": "synthetic_only", "rows": len(truth), "accuracy": float(accuracy_score(truth, guesses)),
        "macro_f1": float(f1.mean()), "weighted_f1": float((f1 * support).sum() / support.sum()),
        "worst_class_recall": float(recall.min()), "label_order": order,
        "confusion_matrix": confusion_matrix(truth, guesses, labels=order).tolist(),
        "per_class": {label: {"precision": float(precision[i]), "recall": float(recall[i]),
            "f1": float(f1[i]), "support": int(support[i])} for i, label in enumerate(order)},
        "zero_division_policy": 0, "unpredicted_labels": [label for label in order if label not in guesses]}

def evaluate(predictions, split="validation", *, final_test_authorized=False):
    if split not in {"validation", "test"}:
        raise ValueError("Evaluation supports validation or final test only")
    if split == "test" and not final_test_authorized:
        raise PermissionError("Final test requires frozen model selection and explicit authorization")
    splits, labels = load_contract()
    return dict(score_predictions(splits[split], predictions, labels), split=split)

def measure_call(function, *args, **kwargs):
    """Time a future fit/predict call; memory is Python-traced allocations, not total RAM."""
    if tracemalloc.is_tracing():
        raise RuntimeError("Separate measurement required; tracemalloc is already active")
    tracemalloc.start()
    start = perf_counter()
    try:
        result = function(*args, **kwargs)
        elapsed = perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, {"wall_seconds": elapsed, "python_traced_peak_bytes": peak,
                    "memory_scope": "Python-traced allocations; native model allocations may be excluded"}

def artifact_size(path):
    """Measure one exported pipeline file without loading it."""
    return Path(path).stat().st_size
