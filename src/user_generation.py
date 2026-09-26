"""
Synthetic user financial data generation.

Generates 10,000 synthetic Indian household financial profiles, grounded
in the real city_master cost-of-living figures so that income/rent/
expense levels are city-appropriate, rather than pulled from a single
national distribution.

Everything here is EXPLICITLY SYNTHETIC. It exists for pipeline testing,
feature-engineering testing, and demonstrating the future ML methodology.
It is NOT real customer data and must never be presented as such.

All synthetic randomness uses NumPy's explicit default_rng(42) generator for reproducibility.
"""

import numpy as np
import pandas as pd
from utils import PROCESSED_DIR, REPORTS_DIR, write_log

N_USERS = 10_000
SEED = 42

OUT = PROCESSED_DIR / "user_financial_data.csv"
LOG = REPORTS_DIR / "user_generation_log.md"

# --- Documented synthetic assumptions (NOT real market data) -----------
# Illustrative monthly rates for household services, used only to
# construct a synthetic household_service_expense feature. These are
# assumptions for pipeline demonstration purposes, not sourced pricing.
ASSUMED_MONTHLY_SERVICE_RATE_INR = {
    "cleaning": 1500,
    "cooking": 4000,
    "dishwashing": 800,
    "laundry": 1000,
}

ANNUAL_INFLATION_ASSUMPTION = 0.05  # planning assumption, see feature_engineering.py

FINANCIAL_GOALS = ["retirement", "child_education", "home_purchase",
                    "emergency_fund", "vehicle_purchase", "wedding", "travel"]
RISK_TOLERANCE = ["low", "medium", "high"]


def generate(city_master: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)

    n = N_USERS
    cities = city_master.sample(n=n, replace=True, random_state=SEED).reset_index(drop=True)

    user_id = np.array([f"U{100000 + i}" for i in range(n)])
    age = rng.integers(22, 65, size=n)

    family_size = rng.integers(1, 7, size=n)
    dependents = np.array([rng.integers(0, fs) if fs > 1 else 0 for fs in family_size])

    # Income: city-appropriate salary as a base, scaled by an
    # individual multiplier (experience/seniority proxy) - synthetic.
    income_multiplier = rng.lognormal(mean=0.0, sigma=0.45, size=n)
    monthly_income = (cities["monthly_salary_after_tax_inr"].values * income_multiplier).round(0)
    monthly_income = np.clip(monthly_income, 8000, None)

    # Rent: city-appropriate rent, only paid by a subset (some own their home)
    owns_home = rng.random(n) < 0.35
    rent = np.where(owns_home, 0, (cities["rent_one_person_inr"].values *
                                    rng.uniform(0.8, 1.6, size=n)).round(0))

    # Household expense buckets, as fractions of income with noise -
    # synthetic allocation, not survey-derived.
    food = (monthly_income * rng.uniform(0.10, 0.22, size=n)).round(0)
    transport = (monthly_income * rng.uniform(0.03, 0.10, size=n)).round(0)
    utilities = (monthly_income * rng.uniform(0.02, 0.06, size=n)).round(0)
    education = np.where(
        dependents > 0,
        (monthly_income * rng.uniform(0.03, 0.15, size=n)).round(0),
        0.0,
    )
    medical = (monthly_income * rng.uniform(0.01, 0.06, size=n)).round(0)

    # Household services - only some households use paid domestic help,
    # more likely at higher income. Uses the documented assumed rates above.
    uses_help_prob = np.clip(monthly_income / monthly_income.max(), 0.05, 0.85)
    uses_cleaning = rng.random(n) < uses_help_prob * 0.5
    uses_cooking = rng.random(n) < uses_help_prob * 0.25
    uses_dishwashing = rng.random(n) < uses_help_prob * 0.3
    uses_laundry = rng.random(n) < uses_help_prob * 0.2
    household_services = (
        uses_cleaning * ASSUMED_MONTHLY_SERVICE_RATE_INR["cleaning"]
        + uses_cooking * ASSUMED_MONTHLY_SERVICE_RATE_INR["cooking"]
        + uses_dishwashing * ASSUMED_MONTHLY_SERVICE_RATE_INR["dishwashing"]
        + uses_laundry * ASSUMED_MONTHLY_SERVICE_RATE_INR["laundry"]
    )

    other_expenses = (monthly_income * rng.uniform(0.02, 0.08, size=n)).round(0)

    monthly_expenses = (rent + food + transport + utilities + education
                         + medical + household_services + other_expenses)

    # Loans / EMI - only some users carry a loan
    has_loan = rng.random(n) < 0.4
    loan_interest_rate = np.where(has_loan, rng.uniform(7.5, 14.0, size=n).round(2), np.nan)
    loan_tenure_years = np.where(has_loan, rng.integers(1, 20, size=n), np.nan)
    emi_amount = np.where(has_loan, (monthly_income * rng.uniform(0.05, 0.35, size=n)).round(0), 0.0)

    assets = (monthly_income * rng.uniform(3, 60, size=n)).round(0)
    liabilities = np.where(has_loan, (emi_amount * loan_tenure_years * 12 * rng.uniform(0.3, 0.9, size=n)).round(0), 0.0)
    investments = (monthly_income * rng.uniform(0, 20, size=n)).round(0)
    savings = np.clip(monthly_income - monthly_expenses - emi_amount, 0, None).round(0)

    financial_goal = rng.choice(FINANCIAL_GOALS, size=n)
    goal_amount = (monthly_income * rng.uniform(12, 200, size=n)).round(0)
    reference_month = pd.to_datetime("2025-01-01") + pd.to_timedelta(
        rng.integers(0, 12, size=n) * 30, unit="D")
    reference_month = reference_month.to_period("M").to_timestamp()
    goal_year = reference_month.year + rng.integers(1, 20, size=n)
    risk_tolerance = rng.choice(RISK_TOLERANCE, size=n)

    df = pd.DataFrame({
        "user_id": user_id,
        "age": age,
        "city": cities["City"].values,
        "city_key": cities["city_key"].values,
        "family_size": family_size,
        "dependents": dependents,
        "monthly_income": monthly_income,
        "owns_home": owns_home,
        "rent": rent,
        "food": food,
        "transport": transport,
        "utilities": utilities,
        "education": education,
        "medical": medical,
        "household_services": household_services,
        "other_expenses": other_expenses,
        "monthly_expenses": monthly_expenses,
        "has_loan": has_loan,
        "emi_amount": emi_amount,
        "loan_interest_rate": loan_interest_rate,
        "loan_tenure_years": loan_tenure_years,
        "assets": assets,
        "liabilities": liabilities,
        "investments": investments,
        "savings": savings,
        "financial_goal": financial_goal,
        "goal_amount": goal_amount,
        "goal_year": goal_year,
        "risk_tolerance": risk_tolerance,
        "reference_month": reference_month,
    })
    return df


def validate(df: pd.DataFrame) -> dict:
    checks = {
        "unique_user_ids": df["user_id"].is_unique,
        "income_positive": (df["monthly_income"] > 0).all(),
        "expenses_nonneg": (df["monthly_expenses"] >= 0).all(),
        "dependents_le_family_size": (df["dependents"] <= df["family_size"]).all(),
        "emi_nonneg": (df["emi_amount"] >= 0).all(),
        "assets_nonneg": (df["assets"] >= 0).all(),
        "liabilities_nonneg": (df["liabilities"] >= 0).all(),
        "investments_nonneg": (df["investments"] >= 0).all(),
        "goal_amount_nonneg": (df["goal_amount"] >= 0).all(),
        "goal_year_after_reference": (df["goal_year"] > df["reference_month"].dt.year).all(),
        "valid_city_reference": df["city_key"].notna().all(),
        "row_count_correct": len(df) == N_USERS,
    }
    return checks


def process():
    city_master = pd.read_csv(PROCESSED_DIR / "city_master.csv")
    df = generate(city_master)
    checks = validate(df)
    df.to_csv(OUT, index=False)

    lines = [
        "# Synthetic User Data Generation Log",
        "",
        f"- Users generated: {len(df)} (target: {N_USERS})",
        f"- Seed: {SEED}",
        "- Explicitly synthetic: grounded in real city_master cost-of-living figures,",
        "  but income/expense allocations, loan terms, and household-service usage are",
        "  documented synthetic assumptions, not observed data.",
        f"- Assumed monthly household-service rates (INR): {ASSUMED_MONTHLY_SERVICE_RATE_INR}",
        "",
        "## Validation",
    ]
    for k, v in checks.items():
        lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    all_pass = all(checks.values())
    lines.append("")
    lines.append(f"Overall: {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED - see above'}")
    lines.append(f"\nOutput: `data/processed/user_financial_data.csv`, shape {df.shape}")
    write_log(LOG, lines)

    print(f"[USERS] generated {len(df)} rows, all checks passed: {all_pass}")
    if not all_pass:
        raise AssertionError(f"Synthetic user validation failed: {checks}")
    return df


if __name__ == "__main__":
    process()
