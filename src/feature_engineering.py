"""
Feature engineering on the integrated user dataset.

All features here are deterministic transformations of columns already
present after integration.py runs. ANNUAL_INFLATION_ASSUMPTION is a
planning assumption (not observed inflation, not a missing-value fix).

The goal_feasibility target is explicitly a RULE-DERIVED / SYNTHETIC
target: it is deterministically computed from the input features, so it
is a methodology-demonstration target, not real-world ground truth. This
is documented in every report that references it.
"""

import numpy as np
import pandas as pd
from utils import PROCESSED_DIR, REPORTS_DIR, write_log

ANNUAL_INFLATION_ASSUMPTION = 0.05

IN_PATH = PROCESSED_DIR / "final_user_dataset_integrated.csv"
OUT_PATH = PROCESSED_DIR / "final_user_dataset.csv"
LOG = REPORTS_DIR / "feature_engineering_log.md"


def safe_div(numerator, denominator):
    return np.where(denominator != 0, numerator / denominator, np.nan)


def engineer(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # monthly_expenses contains recurring non-EMI expenses. Debt service is
    # subtracted separately so that cash available for goals is consistent
    # with the synthetic user's post-EMI savings definition.
    df["disposable_income"] = df["monthly_income"] - df["monthly_expenses"] - df["emi_amount"]
    df["monthly_savings"] = df["disposable_income"]
    df["savings_rate"] = safe_div(df["monthly_savings"], df["monthly_income"])
    df["emi_ratio"] = safe_div(df["emi_amount"], df["monthly_income"])
    df["rent_burden"] = safe_div(df["rent"], df["monthly_income"])
    df["net_worth"] = df["assets"] - df["liabilities"]
    df["household_service_expense_ratio"] = safe_div(df["household_services"], df["monthly_income"])

    ref_year = df["reference_month"].dt.year
    df["goal_horizon_years"] = df["goal_year"] - ref_year

    df["future_goal_cost"] = (
        df["goal_amount"] * (1 + ANNUAL_INFLATION_ASSUMPTION) ** df["goal_horizon_years"]
    )

    # Rule-derived / synthetic baseline target - see module docstring.
    projected_savings = (
        df["monthly_savings"] * 12 * df["goal_horizon_years"] + df["investments"]
    )
    df["projected_savings"] = projected_savings
    df["goal_feasibility"] = (projected_savings >= df["future_goal_cost"]).astype(int)

    return df


def process():
    df = pd.read_csv(IN_PATH, parse_dates=["reference_month", "cpi_month", "rbi_month"])
    out = engineer(df)
    out.to_csv(OUT_PATH, index=False)

    target_counts = out["goal_feasibility"].value_counts().to_dict()
    target_rate = out["goal_feasibility"].mean()

    lines = [
        "# Feature Engineering Log",
        "",
        f"- Input rows: {df.shape[0]}, columns: {df.shape[1]}",
        f"- Output rows: {out.shape[0]}, columns: {out.shape[1]}",
        f"- ANNUAL_INFLATION_ASSUMPTION = {ANNUAL_INFLATION_ASSUMPTION}"
        f" (explicit planning assumption, NOT observed CPI inflation, NOT used to fill any missing value)",
        "",
        "## Rule-derived goal_feasibility target",
        f"- Class counts: {target_counts}",
        f"- Feasible rate: {target_rate:.3f}",
        "- monthly_savings is defined as post-expense, post-EMI cash surplus; investments",
        "  are added separately to projected_savings.",
        "- This target is DETERMINISTICALLY derived from monthly_savings, investments,",
        "  goal_amount and goal_horizon_years in this same row. It demonstrates how a",
        "  future ML target would be structured; it is NOT a real-world observed outcome,",
        "  and high accuracy from any future model trained on it would mainly show the",
        "  model can reproduce the rule, not that it predicts real financial outcomes.",
        "",
        "## Feature summary (describe)",
        out[["disposable_income", "monthly_savings", "savings_rate", "emi_ratio",
             "rent_burden", "net_worth", "goal_horizon_years", "future_goal_cost"]]
        .describe().round(2).to_string(),
    ]
    write_log(LOG, lines)
    print(f"[FEATURES] rows={out.shape[0]}, cols={out.shape[1]}, feasible_rate={target_rate:.3f}")
    return out


if __name__ == "__main__":
    process()
