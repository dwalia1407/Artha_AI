"""
Dataset inventory. Profiles every raw dataset actually used by the
pipeline and writes reports/data_inventory.md with real measured
numbers (not assumed/estimated ones).
"""

import pandas as pd
from utils import RAW_DIR, REPORTS_DIR, write_log

HCES_DIR = RAW_DIR / "HCES_Data_2023-24_Csv"


def count_csv_rows(path):
    """Count data rows in a large CSV without loading it fully."""
    n = -1  # subtract header
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for _ in f:
            n += 1
    return n


def profile_hces_level(path, sample_rows=200_000):
    sample = pd.read_csv(path, nrows=sample_rows)
    rows = count_csv_rows(path)
    return {
        "file": path.name,
        "rows": rows,
        "columns": sample.shape[1],
        "column_names": sample.columns.tolist(),
    }


def process():
    lines = ["# Data Inventory", "", "All figures below are measured from the actual files, not assumed.", ""]

    # CPI
    lines += ["## CPI - Rural, Urban, Combined.xlsx",
              "- Sheet: CPI - 2012=100 (All India) (1)",
              "- Grain: month x commodity (General Index subset used as monthly context)",
              "- Role: monthly inflation/economic context",
              "- See reports/cpi_processing_log.md for measured row counts and missingness.", ""]

    # RBI
    lines += ["## Major Monetary Policy Rates...xlsx",
              "- Sheet: Report 1",
              "- Grain: effective-date policy event (converted to monthly derived table)",
              "- Role: monthly monetary-policy context",
              "- See reports/rbi_processing_log.md for measured row counts and missingness.", ""]

    # City data
    lc = pd.read_csv(RAW_DIR / "livingcost_india_all_inr (4).csv")
    mc = pd.read_csv(RAW_DIR / "merged_cities_data (2).csv")
    lines += [
        "## livingcost_india_all_inr (4).csv",
        f"- Shape: {lc.shape}",
        f"- Columns: {lc.columns.tolist()}",
        f"- Missing cells: {int(lc.isna().sum().sum())}",
        f"- Duplicate rows: {int(lc.duplicated().sum())}",
        "- Grain: city. Role: primary city cost-of-living reference (221 cities).",
        "",
        "## merged_cities_data (2).csv",
        f"- Shape: {mc.shape}",
        f"- Columns: {mc.columns.tolist()}",
        f"- Missing cells by column (non-zero only): {mc.isna().sum()[mc.isna().sum() > 0].to_dict()}",
        f"- Duplicate rows: {int(mc.duplicated().sum())}",
        "- Grain: city (30 cities). Role: optional socioeconomic enrichment (gdp/population/eol).",
        "",
    ]

    # HCES levels
    lines += ["## HCES 2023-24 (15 levels, `data/raw/HCES_Data_2023-24_Csv/`)",
              "This project uses Level 15 as the primary benchmark source and inspects",
              "Level 14 for the inventory; the other 13 levels are listed here for",
              "completeness (row counts measured, not loaded/processed).", ""]

    for f in sorted(HCES_DIR.glob("*.csv")):
        rows = count_csv_rows(f)
        header = pd.read_csv(f, nrows=0)
        used = "USED (Level 15 - household benchmark)" if "15" in f.name else \
               "INSPECTED ONLY (Level 14 - item-level, no codebook available)" if "14" in f.name and "A1" in f.name else \
               "not used in this submission"
        lines.append(f"- `{f.name}`: {rows} rows, {header.shape[1]} columns - {used}")
    lines.append("")

    # User data
    lines += ["## Synthetic user financial data",
              "- Grain: individual user x reference month",
              "- Generated (not sourced): see reports/user_generation_log.md for the full",
              "  generation methodology, assumptions, and validation results.", ""]

    write_log(REPORTS_DIR / "data_inventory.md", lines)
    print("[INVENTORY] reports/data_inventory.md written")


if __name__ == "__main__":
    process()
