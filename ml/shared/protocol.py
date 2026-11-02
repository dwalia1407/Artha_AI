"""Approved data contract and train-only text representation."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "v2"
HASHES = {
    "dataset.csv": "6ded5297a5ee93c6222f0a5f5dc42695e00344fd92ab5ae6478db54e766359ce",
    "label_map.json": "66ce2b82f34cb350a606a45e20d89d8845d28db53d73704d9e4b481972414483",
    "split_manifest.csv": "6357f23cdf8ec343862b3dbc2510e628313b195cf7cfd1ae9e6ca91ef46f92ca",
}
TFIDF_SETTINGS = dict(ngram_range=(1, 2), max_features=2000, lowercase=True,
                      stop_words=None, min_df=1, max_df=1.0, norm="l2")

def read_csv(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def load_contract(folder=CONTRACT):
    folder = Path(folder)
    for name, expected in HASHES.items():
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Unapproved or changed contract file: {name}")
    rows, manifest = read_csv(folder / "dataset.csv"), read_csv(folder / "split_manifest.csv")
    labels = json.loads((folder / "label_map.json").read_text(encoding="utf-8"))
    by_id = {row["transaction_id"]: row for row in manifest}
    ids = [row["transaction_id"] for row in rows]
    if len(by_id) != len(manifest) or len(set(ids)) != len(ids) or set(ids) != set(by_id):
        raise ValueError("Duplicate, missing or extra transaction IDs")
    splits = {name: [] for name in ("train", "validation", "test")}
    groups, texts = defaultdict(set), defaultdict(set)
    for row in rows:
        entry = by_id[row["transaction_id"]]
        if entry["split"] not in splits or entry["group_id"] != row["group_id"]:
            raise ValueError("Invalid split or mismatched group")
        if row["category"] not in labels or not row["description"].strip():
            raise ValueError("Unknown category or empty description")
        splits[entry["split"]].append(row)
        groups[row["group_id"]].add(entry["split"])
        texts[" ".join(row["description"].casefold().split())].add(entry["split"])
    if any(len(value) != 1 for value in [*groups.values(), *texts.values()]):
        raise ValueError("Group or identical-description overlap")
    if {s: len(r) for s, r in splits.items()} != {"train": 375, "validation": 80, "test": 84}:
        raise ValueError("Unexpected split sizes")
    for subset in splits.values():
        counts = Counter(row["category"] for row in subset)
        if set(counts) != set(labels) or min(counts.values()) < 3:
            raise ValueError("Insufficient category coverage")
    return splits, labels

def fit_training_text(training_rows):
    vectorizer = TfidfVectorizer(**TFIDF_SETTINGS)
    matrix = vectorizer.fit_transform([row["description"] for row in training_rows])
    return vectorizer, matrix

def majority_category(training_rows, labels):
    counts = Counter(row["category"] for row in training_rows)
    if not counts or set(counts) - set(labels):
        raise ValueError("Empty training rows or unknown categories")
    return min(labels, key=lambda label: (-counts[label], labels[label]))
