import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Tuple


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> pd.Timestamp:
    """Parse a date string into a pandas Timestamp.
    Returns NaT if parsing fails.
    """
    try:
        return pd.to_datetime(date_str, format=fmt, errors="coerce")
    except Exception:
        return pd.NaT


def month_continuity(series: pd.Series) -> bool:
    """Check that a series of monthly periods (YYYY-MM) is continuous without gaps.
    Expects a DatetimeIndex with monthly frequency.
    """
    if series.empty:
        return True
    dates = pd.to_datetime(series, errors="coerce")
    dates = dates.dropna().sort_values()
    expected = pd.date_range(start=dates.min(), end=dates.max(), freq="MS")
    return dates.isin(expected).all() and len(dates) == len(expected)


def detect_duplicates(df: pd.DataFrame, subset: List[str] = None) -> pd.DataFrame:
    """Return a DataFrame containing duplicate rows based on the given subset of columns.
    If subset is None, all columns are considered.
    """
    dup_mask = df.duplicated(subset=subset, keep=False)
    return df[dup_mask]


def validate_one_to_one(left: pd.Series, right: pd.Series, left_name: str, right_name: str) -> Tuple[bool, str]:
    """Validate that two Series have a one‑to‑one relationship.
    Returns (is_valid, message).
    """
    left_unique = left.nunique()
    right_unique = right.nunique()
    if left_unique != len(left) or right_unique != len(right):
        return False, f"Non‑unique values detected in {left_name} or {right_name}."
    mapping = pd.Series(right.values, index=left.values)
    if mapping.is_unique and mapping.dropna().shape[0] == left_unique:
        return True, "One‑to‑one mapping validated."
    else:
        return False, f"Mapping between {left_name} and {right_name} is not one‑to‑one."


def validate_merge(df_left: pd.DataFrame, df_right: pd.DataFrame, on: List[str]) -> Tuple[bool, str]:
    """Validate that a merge on specified keys will not produce duplicate rows.
    Checks that the join keys are unique in both DataFrames.
    """
    left_dup = df_left.duplicated(subset=on).any()
    right_dup = df_right.duplicated(subset=on).any()
    if left_dup or right_dup:
        return False, f"Duplicate keys found in merge columns {on}. Left dup: {left_dup}, Right dup: {right_dup}."
    return True, "Merge keys are unique on both sides."
