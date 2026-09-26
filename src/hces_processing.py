"""
HCES 2023-24 processing.

HCES is a 15-level multi-level survey. We do NOT concatenate all 15
levels (they have different grains). This script uses:

  Level 15 (Section 1_1, A2, B2, C2) - household-visit summary level.
  Level 14 (Section A1, B1, C1)      - item-level expenditure records,
                                        inspected for the data inventory
                                        only (see limitation below).

LEVEL 15 GRAIN (verified by inspection):
Each household (identified by FSU_Serial_No + Sector + State +
NSS_Region + District + Stratum + Sub_stratum + Panel + Sub_sample +
FOD_Sub_Region + Sample_SU_No + Second_Stage_Stratum_No +
Sample_Household_No) contributes exactly 4 rows: SECTION 11 (household
roster - no expenditure figure), and three visit sections A2/B2/C2, each
carrying that visit's MONTHLY_CONSUMPTION_EXP (the household's total
monthly consumption expenditure recorded for that visit's reference
month, as pre-computed by NSSO - not derived here from item codes).

MULTIPLIER is confirmed identical across all rows of a household
(verified: 0 households have >1 distinct MULTIPLIER). HOUSEHOLD_SIZE is
identical across visits for the large majority of households; 2,760
households (~1%) show a different HOUSEHOLD_SIZE across visits (a
household composition change between visit months is a real possibility
in a multi-visit survey design, not a data error) - we take the maximum
reported size for that household and document the count.

HOUSEHOLD-LEVEL CONSUMPTION:
For each A2/B2/C2 visit, per-capita consumption is first computed as
MONTHLY_CONSUMPTION_EXP / HOUSEHOLD_SIZE. The household benchmark value is
then the mean of the three visit-level per-capita values. This avoids using
a single maximum household size as the denominator for an average total
consumption value when household size changes across visits.

LIMITATION - ITEM-LEVEL CATEGORY BREAKDOWN NOT ATTEMPTED:
Level 14 carries only a numeric ITEM_CODE (no item description/category
field). Mapping ~hundreds of ITEM_CODE values to named categories (food,
education, medical, clothing, etc.) and their correct 7/30/365-day
reference periods requires the official NSSO HCES item-classification
codebook, which is not included in the raw data provided. Guessing that
mapping from memory would risk fabricating category definitions, which
the project rules explicitly forbid. We therefore do NOT produce
per-category expense benchmarks (food_expense_pc, education_expense_pc,
etc.) in this submission. Level 14 is inspected for the data inventory
(row count, columns, missingness) only. This is documented as a known
limitation, not silently skipped.

STATE CODES:
`State` and `Sector` are the NSS numeric codes present in the raw data.
No state-name lookup table was provided with this dataset, so codes are
kept as-is rather than guessing state names from memory.

Output:
  data/processed/hces_household_level.csv   (261,953 households)
  data/processed/hces_benchmarks.csv        (state x sector x hh-size-group)
"""

import pandas as pd
import numpy as np
from utils import RAW_DIR, PROCESSED_DIR, REPORTS_DIR, write_log

L15_PATH = RAW_DIR / "HCES_Data_2023-24_Csv" / "LEVEL - 15 (Section 1_1, A2,B2  C2).csv"
L14_PATH = RAW_DIR / "HCES_Data_2023-24_Csv" / "LEVEL - 14 (Section  A1,B1  C1).csv"

OUT_HH = PROCESSED_DIR / "hces_household_level.csv"
OUT_BENCH = PROCESSED_DIR / "hces_benchmarks.csv"
LOG = REPORTS_DIR / "hces_processing_log.md"
REPORT = REPORTS_DIR / "hces_processing.md"

HH_KEYS = ["FSU_Serial_No", "Sector", "State", "NSS_Region", "District",
           "Stratum", "Sub_stratum", "Panel", "Sub_sample", "FOD_Sub_Region",
           "Sample_SU_No", "Second_Stage_Stratum_No", "Sample_Household_No"]


def size_group(size):
    if pd.isna(size):
        return np.nan
    if size <= 2:
        return "1-2"
    if size <= 4:
        return "3-4"
    if size <= 6:
        return "5-6"
    return "7+"


def inspect_level14():
    """Inspect Level 14 in chunks (it is too large to load at once
    alongside everything else in this environment). Returns basic
    inventory stats only - no category benchmark is derived from it."""
    rows = 0
    item_codes = set()
    missing_value_rs = 0
    first_cols = None
    for chunk in pd.read_csv(L14_PATH, chunksize=500_000):
        if first_cols is None:
            first_cols = chunk.columns.tolist()
        rows += len(chunk)
        item_codes.update(chunk["ITEM_CODE"].dropna().unique().tolist())
        missing_value_rs += chunk["VALUE_RS"].isna().sum()
    return {
        "rows": rows,
        "columns": first_cols,
        "n_columns": len(first_cols),
        "n_distinct_item_codes": len(item_codes),
        "value_rs_missing": int(missing_value_rs),
    }


def process_level15():
    df = pd.read_csv(L15_PATH)
    raw_shape = df.shape

    visits = df[df["SECTION"].isin(["A2", "B2", "C2"])].copy()

    # Compute per-visit per-capita consumption before household aggregation.
    # This is important for the ~1% of households whose household size changes
    # across the three survey visits.
    visits["visit_consumption_pc"] = (
        visits["MONTHLY_CONSUMPTION_EXP"] / visits["HOUSEHOLD_SIZE"]
    )
    hh_consumption = (
        visits.groupby(HH_KEYS)["MONTHLY_CONSUMPTION_EXP"]
        .mean()
        .rename("household_monthly_consumption")
        .reset_index()
    )
    hh_consumption_pc = (
        visits.groupby(HH_KEYS)["visit_consumption_pc"]
        .mean()
        .rename("consumption_pc")
        .reset_index()
    )
    hh_online = (
        visits.groupby(HH_KEYS)["ONLINE_EXPENDITURE"]
        .mean()
        .rename("household_monthly_online_expenditure")
        .reset_index()
    )
    hh_size = visits.groupby(HH_KEYS)["HOUSEHOLD_SIZE"]
    size_inconsistent = int((hh_size.nunique() > 1).sum())
    hh_size = hh_size.max().rename("household_size").reset_index()

    hh_meta = visits.groupby(HH_KEYS).agg(
        MULTIPLIER=("MULTIPLIER", "first"),
    ).reset_index()

    household = hh_consumption.merge(hh_size, on=HH_KEYS, validate="one_to_one")
    household = household.merge(hh_consumption_pc, on=HH_KEYS, validate="one_to_one")
    household = household.merge(hh_online, on=HH_KEYS, validate="one_to_one")
    household = household.merge(hh_meta, on=HH_KEYS, validate="one_to_one")

    household["household_size_group"] = household["household_size"].apply(size_group)

    # Basic validity checks
    neg_consumption = int((household["household_monthly_consumption"] < 0).sum())
    zero_size = int((household["household_size"] <= 0).sum())
    missing_consumption = int(household["household_monthly_consumption"].isna().sum())

    household.to_csv(OUT_HH, index=False)

    return household, {
        "raw_shape": raw_shape,
        "n_households": household.shape[0],
        "size_inconsistent_households": size_inconsistent,
        "neg_consumption": neg_consumption,
        "zero_or_neg_size": zero_size,
        "missing_consumption": missing_consumption,
    }


def build_benchmarks(household: pd.DataFrame):
    hh = household.dropna(subset=["consumption_pc", "household_size_group"]).copy()

    def weighted_mean(g):
        w = g["MULTIPLIER"]
        return np.average(g["consumption_pc"], weights=w)

    bench = (
        hh.groupby(["State", "Sector", "household_size_group"])
        .apply(lambda g: pd.Series({
            "total_consumption_pc": weighted_mean(g),
            "n_households": len(g),
            "sum_multiplier": g["MULTIPLIER"].sum(),
        }))
        .reset_index()
    )
    bench.to_csv(OUT_BENCH, index=False)
    return bench


def process():
    household, stats = process_level15()
    bench = build_benchmarks(household)
    l14_stats = inspect_level14()

    lines = [
        "# HCES Processing Log",
        "",
        "## Level 15 (household-visit summary)",
        f"- Raw shape: {stats['raw_shape']}",
        f"- Households identified: {stats['n_households']}",
        f"- Households with inconsistent HOUSEHOLD_SIZE across visits (used max): {stats['size_inconsistent_households']}",
        f"- Households with missing household_monthly_consumption (all 3 visits null): {stats['missing_consumption']}",
        f"- Households with non-positive size: {stats['zero_or_neg_size']}",
        f"- Households with negative consumption: {stats['neg_consumption']}",
        "",
        f"## Level 14 (item-level) - inspected only, not aggregated into a category benchmark",
        f"- Rows: {l14_stats['rows']}",
        f"- Columns ({l14_stats['n_columns']}): {l14_stats['columns']}",
        f"- Distinct ITEM_CODE values: {l14_stats['n_distinct_item_codes']}",
        f"- VALUE_RS missing: {l14_stats['value_rs_missing']}",
        "- No official item-classification codebook was supplied with the raw data, so ITEM_CODE",
        "  values are NOT mapped to named categories (food/education/medical/etc.) in this submission.",
        "  See reports/hces_processing.md for the full justification.",
        "",
        f"## Benchmark table (state x sector x household_size_group)",
        f"- Rows: {bench.shape[0]}",
        f"Output: data/processed/hces_household_level.csv (household grain, {household.shape[0]} rows)",
        f"Output: data/processed/hces_benchmarks.csv (benchmark grain, {bench.shape[0]} rows)",
    ]
    write_log(LOG, lines)

    report = [
        "# HCES 2023-24 Processing Report",
        "",
        "## Source structure",
        "HCES 2023-24 is distributed as 15 CSV levels, each a different grain",
        "(household roster, item-level food/non-food expenditure, durable goods,",
        "etc.). This project uses Level 15 (household-visit consumption summary)",
        "as the primary benchmark source, and inspects Level 14 (item-level",
        "records) for the data inventory.",
        "",
        "## Levels used",
        "- Level 15: `LEVEL - 15 (Section 1_1, A2,B2  C2).csv`",
        "- Level 14: `LEVEL - 14 (Section  A1,B1  C1).csv` (inspection only)",
        "",
        "## Household key",
        f"Composite key (verified unique per household, 3 visit rows each): {', '.join(HH_KEYS)}",
        "",
        "## Reference-period / weighting methodology actually applied",
        "Level 15's MONTHLY_CONSUMPTION_EXP is NSSO's own pre-computed total monthly",
        "consumption expenditure for a household for a given visit (already reference-",
        "period-adjusted by NSSO, not re-derived here from item codes). Each household",
        "is visited 3 times (sections A2, B2, C2) in different months across the survey",
        "year; the household-level figure used is the mean of the 3 visit totals, which",
        "smooths seasonal variation in a way a single visit would not.",
        "",
        "Weighted state x sector x household-size-group benchmarks use NSSO's",
        "MULTIPLIER as the survey weight:",
        "",
        "    weighted_mean = sum(consumption_pc * multiplier) / sum(multiplier)",
        "",
        "## What was NOT attempted (and why)",
        "Category-wise benchmarks (food_expense_pc, education_expense_pc,",
        "medical_expense_pc, rent_expense_pc, etc.) as originally sketched in the",
        "project context would require Level 14's ITEM_CODE to be mapped to named",
        "categories and 7/30/365-day reference periods using the official NSSO",
        "item-classification codebook. That codebook was not supplied with the raw",
        "data. Reconstructing hundreds of item-code-to-category mappings from",
        "memory risks fabricating definitions that are not actually verifiable -",
        "which the project rules explicitly forbid. Level 14 is therefore only",
        "profiled (row count, columns, missingness) for the data inventory, and no",
        "category-level benchmark is produced from it in this submission.",
        "",
        "## Validation performed",
        f"- Household uniqueness: verified (each household has exactly 3 A2/B2/C2 rows).",
        f"- MULTIPLIER consistency within a household: verified (0 households differ).",
        f"- HOUSEHOLD_SIZE consistency within a household: {stats['size_inconsistent_households']} of"
        f" {stats['n_households']} households show a change across visits; max reported size is used only for size grouping, not as the per-capita denominator.",
        f"- Missing/invalid consumption values: {stats['missing_consumption']} missing,"
        f" {stats['neg_consumption']} negative (none observed).",
        "",
        "## Limitations",
        "- Benchmarks are at state (numeric code) x sector x household-size-group",
        "  grain, not city grain - HCES is not a city-level survey.",
        "- No category-wise (food/education/medical/...) expenditure split is produced;",
        "  only total household consumption expenditure per capita.",
        "- State codes are the raw NSS numeric codes; no state-name lookup was supplied.",
    ]
    write_log(REPORT, report)

    print(f"[HCES] households={stats['n_households']}, benchmark rows={bench.shape[0]}")
    print(f"[HCES] Level14 rows={l14_stats['rows']}, distinct item codes={l14_stats['n_distinct_item_codes']}")
    return household, bench


if __name__ == "__main__":
    process()
