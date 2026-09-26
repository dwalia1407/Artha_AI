"""
Automated data validation + outlier analysis on the final integrated,
feature-engineered dataset.

Outliers are FLAGGED and reported, never silently deleted - a high
income, asset value, or investment can be a legitimate financial
extreme, not a data-entry error.
"""

import pandas as pd
import numpy as np
from utils import PROCESSED_DIR, REPORTS_DIR, TABLES_DIR, write_log, iqr_outlier_bounds

IN_PATH = PROCESSED_DIR / "final_user_dataset.csv"
LOG = REPORTS_DIR / "data_quality_report.md"
SUMMARY_CSV = TABLES_DIR / "data_quality_summary.csv"
OUTLIER_CSV = TABLES_DIR / "outlier_summary.csv"

REQUIRED_COLUMNS = [
    "user_id", "age", "city", "city_key", "family_size", "dependents",
    "monthly_income", "rent", "monthly_expenses", "emi_amount", "assets",
    "liabilities", "investments", "savings", "goal_amount", "goal_year",
    "reference_month", "disposable_income", "monthly_savings",
    "savings_rate", "emi_ratio", "rent_burden", "net_worth",
    "goal_horizon_years", "future_goal_cost", "goal_feasibility",
]

OUTLIER_COLUMNS = ["monthly_income", "monthly_expenses", "monthly_savings",
                    "emi_amount", "assets", "liabilities", "investments", "goal_amount"]


def schema_checks(df):
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return {
        "all_required_columns_present": len(missing_cols) == 0,
        "missing_columns": missing_cols,
    }


def identifier_checks(df):
    return {
        "unique_user_ids": bool(df["user_id"].is_unique),
        "valid_city_keys": bool(df["city_key"].notna().all()),
    }


def range_checks(df):
    return {
        "income_positive": bool((df["monthly_income"] > 0).all()),
        "expenses_nonneg": bool((df["monthly_expenses"] >= 0).all()),
        "assets_nonneg": bool((df["assets"] >= 0).all()),
        "liabilities_nonneg": bool((df["liabilities"] >= 0).all()),
        "investments_nonneg": bool((df["investments"] >= 0).all()),
        "family_size_ge1": bool((df["family_size"] >= 1).all()),
        "dependents_nonneg": bool((df["dependents"] >= 0).all()),
        "dependents_le_family_size": bool((df["dependents"] <= df["family_size"]).all()),
        "goal_amount_nonneg": bool((df["goal_amount"] >= 0).all()),
        "goal_horizon_nonneg": bool((df["goal_horizon_years"] >= 0).all()),
    }


def date_checks(df):
    cpi = pd.read_csv(PROCESSED_DIR / "cpi_monthly_clean.csv", parse_dates=["month"])
    rbi = pd.read_csv(PROCESSED_DIR / "rbi_monthly_clean.csv", parse_dates=["month"])
    return {
        "valid_reference_month": bool(pd.to_datetime(df["reference_month"], errors="coerce").notna().all()),
        "cpi_monthly_continuity_gaps": int(
            len(pd.date_range(cpi["month"].min(), cpi["month"].max(), freq="MS").difference(cpi["month"]))
        ),
        "rbi_monthly_continuity_gaps": int(
            len(pd.date_range(rbi["month"].min(), rbi["month"].max(), freq="MS").difference(rbi["month"]))
        ),
    }


def merge_checks(df, users_raw_rows):
    return {
        "no_unexplained_user_loss": bool(len(df) == users_raw_rows),
        "no_row_multiplication": bool(len(df) == users_raw_rows),
    }


def target_checks(df):
    counts = df["goal_feasibility"].value_counts().to_dict()
    return {
        "target_values_valid_binary": bool(set(df["goal_feasibility"].unique()) <= {0, 1}),
        "class_counts": {int(k): int(v) for k, v in counts.items()},
        "class_balance_pct": {int(k): round(v / len(df) * 100, 2) for k, v in counts.items()},
    }


def missing_data_summary(df):
    miss = df.isna().sum()
    miss = miss[miss > 0]
    return miss.to_dict()


def outlier_analysis(df):
    rows = []
    for col in OUTLIER_COLUMNS:
        lower, upper = iqr_outlier_bounds(df[col])
        n_low = int((df[col] < lower).sum())
        n_high = int((df[col] > upper).sum())
        rows.append({
            "column": col, "q1": round(df[col].quantile(0.25), 2),
            "q3": round(df[col].quantile(0.75), 2),
            "iqr_lower_bound": round(lower, 2), "iqr_upper_bound": round(upper, 2),
            "n_below_lower": n_low, "n_above_upper": n_high,
            "pct_flagged": round((n_low + n_high) / len(df) * 100, 2),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUTLIER_CSV, index=False)
    return out


def process():
    df = pd.read_csv(IN_PATH, parse_dates=["reference_month"])
    users_raw = pd.read_csv(PROCESSED_DIR / "user_financial_data.csv")

    schema = schema_checks(df)
    ident = identifier_checks(df)
    ranges = range_checks(df)
    dates = date_checks(df)
    merges = merge_checks(df, len(users_raw))
    target = target_checks(df)
    missing = missing_data_summary(df)
    outliers = outlier_analysis(df)

    all_bool_checks = {**{f"schema.{k}": v for k, v in schema.items() if k != "missing_columns"},
                        **{f"id.{k}": v for k, v in ident.items()},
                        **{f"range.{k}": v for k, v in ranges.items()},
                        **{f"merge.{k}": v for k, v in merges.items()},
                        **{f"target.{k}": v for k, v in target.items() if k == "target_values_valid_binary"}}
    overall_pass = all(v for v in all_bool_checks.values() if isinstance(v, bool))

    lines = [
        "# Data Quality Report",
        "",
        f"Final dataset: `data/processed/final_user_dataset.csv`, shape {df.shape}",
        "",
        "## Schema validation",
    ]
    for k, v in schema.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Identifier validation")
    for k, v in ident.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Range validation")
    for k, v in ranges.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Date / continuity validation")
    for k, v in dates.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Merge validation")
    for k, v in merges.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Target validation (rule-derived goal_feasibility)")
    for k, v in target.items():
        lines.append(f"- {k}: {v}")
    lines.append("\n## Missing data (final dataset, non-zero columns only)")
    if missing:
        for k, v in missing.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("- No missing values in the final dataset.")
    lines.append("\n## Outlier analysis (IQR method, flagged not removed)")
    lines.append(outliers.to_string(index=False))
    lines.append("")
    lines.append("Outliers are NOT automatically deleted. A high income, large asset base, or")
    lines.append("large investment is plausible for a real household; this table exists to")
    lines.append("surface extremes for review, not to justify silent trimming.")
    lines.append("")
    lines.append(f"## Overall status: {'PASS' if overall_pass else 'FAIL - see above'}")

    write_log(LOG, lines)

    # small machine-readable summary
    summary_rows = []
    for section, checks in [("schema", schema), ("identifier", ident), ("range", ranges), ("merge", merges)]:
        for k, v in checks.items():
            if isinstance(v, bool):
                summary_rows.append({"section": section, "check": k, "result": "PASS" if v else "FAIL"})
    pd.DataFrame(summary_rows).to_csv(SUMMARY_CSV, index=False)

    print(f"[VALIDATION] overall_pass={overall_pass}")
    if not overall_pass:
        raise AssertionError(f"Validation failed: {all_bool_checks}")
    return df


if __name__ == "__main__":
    process()
