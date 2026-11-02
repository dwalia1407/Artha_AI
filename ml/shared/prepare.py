"""Run from project root: python -m ml.shared.prepare. Does not transform test text."""
import csv
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter

import joblib
import numpy
import scipy
import sklearn
from scipy.sparse import save_npz

from .protocol import HASHES, TFIDF_SETTINGS, fit_training_text, load_contract

def prepare(output):
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    splits, _ = load_contract()
    start = perf_counter()
    vectorizer, train = fit_training_text(splits["train"])
    fit_seconds = perf_counter() - start
    validation = vectorizer.transform([r["description"] for r in splits["validation"]])
    output.mkdir(parents=True)
    joblib.dump(vectorizer, output / "tfidf.joblib")
    for name, matrix in [("train", train), ("validation", validation)]:
        save_npz(output / f"{name}.npz", matrix)
        with (output / f"{name}_rows.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["transaction_id", "category"])
            writer.writeheader()
            writer.writerows({k: r[k] for k in writer.fieldnames} for r in splits[name])
    report = {"protocol_version": 2, "source_hashes": HASHES, "tfidf_settings": TFIDF_SETTINGS,
        "features": len(vectorizer.vocabulary_), "train_shape": train.shape, "validation_shape": validation.shape,
        "preprocessing_fit_seconds": fit_seconds, "test_transformed": False, "classifiers_trained": False,
        "versions": {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__,
                     "scikit-learn": sklearn.__version__, "joblib": joblib.__version__},
        "artifact_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}}
    (output / "preparation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report

if __name__ == "__main__":
    print(json.dumps(prepare(Path(__file__).resolve().parents[1] / "artifacts" / "shared_v2"), indent=2))
