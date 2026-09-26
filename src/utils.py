"""
Shared utility functions used across the Artha AI data pipeline.

Kept deliberately small and dependency-free (pandas/numpy only) so a
Semester 3 engineering student can read every line.
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
HIDDEN_DIR = ROOT_DIR / "data" / "hidden"
REPORTS_DIR = ROOT_DIR / "reports"
RESULTS_DIR = ROOT_DIR / "results"
EDA_DIR = RESULTS_DIR / "eda"
TABLES_DIR = RESULTS_DIR / "tables"

for d in [PROCESSED_DIR, HIDDEN_DIR, REPORTS_DIR, EDA_DIR, TABLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def make_city_key(series: pd.Series) -> pd.Series:
    """Normalized join key for city names. Never overwrites the display name."""
    return series.astype(str).str.strip().str.lower()


def check_duplicates(df: pd.DataFrame, subset=None) -> int:
    """Return count of duplicate rows (by subset of columns, or all columns)."""
    return int(df.duplicated(subset=subset).sum())


def validate_merge_keys(left: pd.DataFrame, right: pd.DataFrame, on, how_expected="one_to_one") -> dict:
    """
    Check whether a merge on `on` will behave as expected before doing it.
    Returns a dict report instead of raising, so callers can log + decide.
    """
    left_dup = left.duplicated(subset=on).sum()
    right_dup = right.duplicated(subset=on).sum()
    report = {
        "left_rows": len(left),
        "right_rows": len(right),
        "left_dup_keys": int(left_dup),
        "right_dup_keys": int(right_dup),
        "expected_relationship": how_expected,
        "ok_for_one_to_one": bool(left_dup == 0 and right_dup == 0),
    }
    return report


def write_log(path: Path, lines) -> None:
    """Write a list of strings to a markdown/text file, one per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def append_log(path: Path, lines) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    """Return a small dataframe of missing counts and percentages per column."""
    miss = df.isna().sum()
    pct = (miss / len(df) * 100).round(2) if len(df) else miss * 0
    return pd.DataFrame({"column": miss.index, "missing_count": miss.values, "missing_pct": pct.values})


def iqr_outlier_bounds(series: pd.Series, k: float = 1.5):
    """Return (lower, upper) Tukey IQR bounds for a numeric series."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr
