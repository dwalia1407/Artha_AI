"""
Final integration: USER x CITY x CPI(monthly) x RBI(monthly) x HCES(benchmark)

Grain: ONE USER + ONE REFERENCE MONTH + ONE CITY (per project's Model
Grain definition). Each user row already has exactly one city and one
reference_month, so this is a set of left-joins on:
  - city_key                    -> city context
  - reference_month -> month    -> CPI monthly context
  - reference_month -> month    -> RBI monthly context

HCES is NOT joined by city (HCES benchmarks are state x sector x
household-size-group, and the synthetic users do not carry a state/
sector code - only a city). Forcing a city->state guess would violate
the "never guess mappings" rule, so HCES context is intentionally left
unjoined to the per-user table in this submission; it remains available
as a separate reference table (data/processed/hces_benchmarks.csv) for
future work once users carry a genuine state/sector field. This is
documented as a limitation, not silently skipped.

Every merge below is validated for row-count and key-uniqueness before
and after.
"""

import pandas as pd
from utils import PROCESSED_DIR, REPORTS_DIR, write_log

OUT = PROCESSED_DIR / "final_user_dataset_integrated.csv"
LOG = REPORTS_DIR / "integration_log.md"


def process():
    users = pd.read_csv(PROCESSED_DIR / "user_financial_data.csv", parse_dates=["reference_month"])
    city = pd.read_csv(PROCESSED_DIR / "city_master.csv")
    cpi = pd.read_csv(PROCESSED_DIR / "cpi_monthly_clean.csv", parse_dates=["month"])
    rbi = pd.read_csv(PROCESSED_DIR / "rbi_monthly_clean.csv", parse_dates=["month"])

    rows_before = users.shape[0]

    # --- USER + CITY ---
    city_dup = int(city["city_key"].duplicated().sum())
    users_city = users.merge(
        city.drop(columns=["City"]).add_prefix("city_"),
        left_on="city_key", right_on="city_city_key",
        how="left", validate="many_to_one",
    ).drop(columns=["city_city_key"])
    unmatched_city = int(users_city["city_cost_one_person_inr"].isna().sum())

    # --- + CPI monthly (General Index only, one row per month) ---
    cpi_small = cpi.rename(columns={"month": "cpi_month"}).add_prefix("cpi_").rename(columns={"cpi_cpi_month": "cpi_month"})
    cpi_dup = int(cpi["month"].duplicated().sum())
    merged = users_city.merge(
        cpi_small, left_on="reference_month", right_on="cpi_month",
        how="left", validate="many_to_one",
    )
    unmatched_cpi = int(merged["cpi_combined_index"].isna().sum())

    # --- + RBI monthly ---
    rbi_small = rbi.rename(columns={"month": "rbi_month"}).add_prefix("rbi_").rename(columns={"rbi_rbi_month": "rbi_month"})
    rbi_dup = int(rbi["month"].duplicated().sum())
    merged = merged.merge(
        rbi_small, left_on="reference_month", right_on="rbi_month",
        how="left", validate="many_to_one",
    )
    unmatched_rbi = int(merged["rbi_repo_rate"].isna().sum())

    rows_after = merged.shape[0]

    merged.to_csv(OUT, index=False)

    lines = [
        "# Integration Log",
        "",
        f"- User rows before integration: {rows_before}",
        f"- Rows after all left-joins: {rows_after} (must equal {rows_before} - left joins on unique keys never multiply rows)",
        "",
        "## USER + CITY",
        f"- city_master duplicate city_key: {city_dup}",
        f"- users unmatched to a city (should be 0, users were sampled from city_master): {unmatched_city}",
        "",
        "## + CPI monthly",
        f"- cpi_monthly_clean duplicate month: {cpi_dup}",
        f"- users unmatched to a CPI month: {unmatched_cpi}",
        "",
        "## + RBI monthly",
        f"- rbi_monthly_clean duplicate month: {rbi_dup}",
        f"- users unmatched to an RBI month: {unmatched_rbi}",
        "",
        "## HCES benchmark - intentionally NOT joined here",
        "Synthetic users carry a city, not an NSS state/sector code, and HCES benchmarks",
        "are indexed by state x sector x household-size-group. Guessing a city->state",
        "mapping to force a join would violate the project's 'never guess mappings' rule.",
        "data/processed/hces_benchmarks.csv remains available as a standalone reference",
        "table; joining it correctly is future work once users carry a genuine state field.",
        "",
        f"Output: `data/processed/final_user_dataset_integrated.csv`, shape {merged.shape}",
    ]
    write_log(LOG, lines)
    print(f"[INTEGRATION] rows={rows_after} (expected {rows_before}), "
          f"unmatched city={unmatched_city}, cpi={unmatched_cpi}, rbi={unmatched_rbi}")
    if rows_after != rows_before:
        raise AssertionError("Row count changed during integration - unexpected row multiplication!")
    return merged


if __name__ == "__main__":
    process()
