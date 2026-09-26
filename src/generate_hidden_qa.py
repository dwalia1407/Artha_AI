"""
Hidden QA generation.

Generates a small held-out set of input rows (with known, independently
computed expected outputs) for the finalized feature-engineering logic.
This validates preprocessing/feature calculations on cases NOT used to
tune the pipeline itself. No ML predictions are involved - this is
pipeline QA, not model evaluation.
"""

import pandas as pd
import numpy as np
from utils import HIDDEN_DIR, REPORTS_DIR, write_log
from feature_engineering import engineer, ANNUAL_INFLATION_ASSUMPTION

INPUT_CSV = HIDDEN_DIR / "hidden_qa_input.csv"
EXPECTED_CSV = HIDDEN_DIR / "hidden_qa_expected.csv"


def build_inputs():
    rows = [
        dict(user_id="H001", monthly_income=40000, rent=10000, food=6000, utilities=1500,
             medical=1000, emi_amount=5000, monthly_expenses=10000+6000+1500+1000+2000+2500,
             assets=300000, liabilities=80000, investments=50000, household_services=2000,
             goal_amount=600000, goal_year=2028, reference_month="2025-01-01",
             cpi_month="2025-01-01", rbi_month="2025-01-01"),
        dict(user_id="H002", monthly_income=15000, rent=6000, food=4000, utilities=800,
             medical=500, emi_amount=1000, monthly_expenses=6000+4000+800+500+500+700,
             assets=20000, liabilities=5000, investments=1000, household_services=0,
             goal_amount=100000, goal_year=2026, reference_month="2025-06-01",
             cpi_month="2025-06-01", rbi_month="2025-06-01"),
        dict(user_id="H003", monthly_income=60000, rent=0, food=8000, utilities=2000,
             medical=1500, emi_amount=15000, monthly_expenses=0+8000+2000+1500+3000+3500,
             assets=1200000, liabilities=400000, investments=300000, household_services=3000,
             goal_amount=2000000, goal_year=2035, reference_month="2025-03-01",
             cpi_month="2025-03-01", rbi_month="2025-03-01"),
        dict(user_id="H004", monthly_income=25000, rent=9000, food=5000, utilities=1200,
             medical=800, emi_amount=12000, monthly_expenses=9000+5000+1200+800+1500+1500,
             assets=50000, liabilities=200000, investments=5000, household_services=0,
             goal_amount=300000, goal_year=2027, reference_month="2025-09-01",
             cpi_month="2025-09-01", rbi_month="2025-09-01"),
    ]
    return pd.DataFrame(rows)


def compute_expected(df: pd.DataFrame) -> pd.DataFrame:
    """Independently compute expected feature values (same formulas as
    feature_engineering.py, written out explicitly here so the hidden
    QA is a genuine check of engineer(), not a tautology)."""
    df = df.copy()
    df["reference_month"] = pd.to_datetime(df["reference_month"])
    exp = pd.DataFrame({"user_id": df["user_id"]})
    exp["disposable_income"] = df["monthly_income"] - df["monthly_expenses"] - df["emi_amount"]
    exp["monthly_savings"] = exp["disposable_income"]
    exp["savings_rate"] = exp["monthly_savings"] / df["monthly_income"]
    exp["emi_ratio"] = df["emi_amount"] / df["monthly_income"]
    exp["rent_burden"] = df["rent"] / df["monthly_income"]
    exp["net_worth"] = df["assets"] - df["liabilities"]
    exp["goal_horizon_years"] = df["goal_year"] - df["reference_month"].dt.year
    exp["future_goal_cost"] = df["goal_amount"] * (1 + ANNUAL_INFLATION_ASSUMPTION) ** exp["goal_horizon_years"]
    projected = exp["monthly_savings"] * 12 * exp["goal_horizon_years"] + df["investments"]
    exp["goal_feasibility"] = (projected >= exp["future_goal_cost"]).astype(int)
    return exp


def process():
    inputs = build_inputs()
    expected = compute_expected(inputs)

    inputs.to_csv(INPUT_CSV, index=False)
    expected.to_csv(EXPECTED_CSV, index=False)

    # Actually run the real pipeline function and diff against the
    # independently-computed expected values.
    df_for_engine = inputs.copy()
    df_for_engine["reference_month"] = pd.to_datetime(df_for_engine["reference_month"])
    df_for_engine["cpi_month"] = pd.to_datetime(df_for_engine["cpi_month"])
    df_for_engine["rbi_month"] = pd.to_datetime(df_for_engine["rbi_month"])
    actual = engineer(df_for_engine)

    compare_cols = ["disposable_income", "monthly_savings", "savings_rate", "emi_ratio",
                     "rent_burden", "net_worth", "goal_horizon_years", "future_goal_cost",
                     "goal_feasibility"]
    mismatches = []
    for col in compare_cols:
        diff = (actual[col].reset_index(drop=True) - expected[col].reset_index(drop=True)).abs()
        if (diff > 1e-6).any():
            mismatches.append(col)

    lines = [
        "# Hidden QA",
        "",
        f"- Hidden input rows: {len(inputs)}",
        f"- Columns checked against independently computed expected values: {compare_cols}",
        f"- Mismatched columns: {mismatches if mismatches else 'none'}",
        f"- Overall: {'ALL MATCH' if not mismatches else 'MISMATCH FOUND - see above'}",
        "",
        "Expected values were computed with formulas written independently in",
        "feature_engineering.py (see generate_hidden_qa.py `compute_expected`), not by calling",
        "the pipeline function on itself, so this is a genuine cross-check rather than a",
        "tautological pass.",
    ]
    write_log(REPORTS_DIR / "hidden_qa_log.md", lines)
    print(f"[HIDDEN QA] mismatches={mismatches if mismatches else 'none'}")
    if mismatches:
        raise AssertionError(f"Hidden QA mismatch in columns: {mismatches}")
    return inputs, expected


if __name__ == "__main__":
    process()
