"""
CPI processing.

Source workbook: data/raw/CPI - Rural, Urban, Combined.xlsx
Sheet: "CPI - 2012=100 (All India) (1)"

The workbook has a report-style header (title rows, then a two-row
column header spanning merged cells). We read it with header=None,
locate the real header row, then slice the data below it.

Output: data/processed/cpi_monthly_clean.csv (General Index only,
month x commodity="General Index" grain -> effectively one row per month)
"""

import pandas as pd
from utils import RAW_DIR, PROCESSED_DIR, REPORTS_DIR, write_log

SRC = RAW_DIR / "CPI - Rural, Urban, Combined.xlsx"
SHEET = "CPI - 2012=100 (All India) (1)"
OUT = PROCESSED_DIR / "cpi_monthly_clean.csv"
LOG = REPORTS_DIR / "cpi_processing_log.md"


def load_raw():
    raw = pd.read_excel(SRC, sheet_name=SHEET, header=None)
    return raw


def find_header_row(raw: pd.DataFrame) -> int:
    """The row that literally contains the word 'Month' in some column."""
    for i in range(min(15, len(raw))):
        row_vals = raw.iloc[i].astype(str).str.strip().tolist()
        if "Month" in row_vals:
            return i
    raise ValueError("Could not locate header row containing 'Month'")


def clean():
    raw = load_raw()
    header_row = find_header_row(raw)
    # Header spans two rows (labels row, then Index/Inflation sub-row)
    data = raw.iloc[header_row + 2:].reset_index(drop=True)

    data.columns = [
        "_blank", "month", "commodity", "status",
        "rural_index", "rural_inflation",
        "urban_index", "urban_inflation",
        "combined_index", "combined_inflation",
    ]
    data = data.drop(columns=["_blank"])

    # Drop fully empty rows (trailing blank rows in the sheet)
    data = data.dropna(subset=["month", "commodity"], how="any")

    raw_shape = data.shape

    # Parse month: format is like "DEC-2025"
    data["month"] = pd.to_datetime(data["month"], format="%b-%Y", errors="coerce")
    bad_month_rows = data["month"].isna().sum()
    data = data.dropna(subset=["month"])

    data["commodity"] = data["commodity"].astype(str).str.strip()
    data["status"] = data["status"].astype(str).str.strip()

    numeric_cols = ["rural_index", "rural_inflation", "urban_index",
                     "urban_inflation", "combined_index", "combined_inflation"]
    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    # Remove exact duplicate rows (same month+commodity+status+values)
    dup_before = data.duplicated().sum()
    data = data.drop_duplicates()

    data = data.sort_values(["month", "commodity"]).reset_index(drop=True)

    cleaned_full_shape = data.shape

    # --- General Index monthly series (the "monthly economic context") ---
    gi = data[data["commodity"] == "A) General Index"].copy()
    if gi.empty:
        # fall back: some workbook exports label it just "General Index"
        gi = data[data["commodity"].str.contains("General Index", case=False, na=False)].copy()
    gi = gi.sort_values("month").reset_index(drop=True)

    dup_months_raw = gi["month"].duplicated().sum()

    # The source workbook carries both a "Provisional" and a later "Final"
    # release for the same month once the Final figure is published. Both
    # releases were observed to carry identical index/inflation values in
    # this workbook, but Final is the authoritative release, so we keep one
    # row per month and prefer Final over Provisional (most recent months
    # only have Provisional, since Final has not been released yet).
    status_rank = {"Final": 0, "Provisional": 1}
    gi["_status_rank"] = gi["status"].map(status_rank).fillna(2)
    gi = gi.sort_values(["month", "_status_rank"]).drop_duplicates(subset="month", keep="first")
    gi = gi.drop(columns="_status_rank").sort_values("month").reset_index(drop=True)

    dup_months = gi["month"].duplicated().sum()
    full_range = pd.date_range(gi["month"].min(), gi["month"].max(), freq="MS")
    missing_months = full_range.difference(gi["month"])

    index_missing = gi["combined_index"].isna().sum()
    inflation_missing = gi["combined_inflation"].isna().sum()

    gi_out = gi[["month", "commodity", "status",
                 "rural_index", "rural_inflation",
                 "urban_index", "urban_inflation",
                 "combined_index", "combined_inflation"]].copy()
    gi_out.to_csv(OUT, index=False)

    lines = [
        "# CPI Processing Log",
        "",
        f"- Source workbook sheet: `{SHEET}`",
        f"- Header row located at raw row index: {header_row}",
        f"- Raw data rows after header slice (before cleaning): {raw_shape[0]}",
        f"- Rows dropped for unparsable month/commodity: n/a (dropna on month/commodity applied first)",
        f"- Rows with unparsable month value (dropped): {bad_month_rows}",
        f"- Exact duplicate rows removed: {dup_before}",
        f"- Cleaned full table shape (all commodities): {cleaned_full_shape}",
        "",
        "## General Index monthly series",
        f"- Raw General Index rows before Provisional/Final dedup: {raw_shape[0] if False else dup_months_raw + gi.shape[0]}",
        f"- Duplicate (Provisional+Final) month rows collapsed: {dup_months_raw} (kept Final where available, else Provisional)",
        f"- Rows: {gi.shape[0]}",
        f"- Date range: {gi['month'].min().date()} -> {gi['month'].max().date()}",
        f"- Duplicate months in General Index series: {dup_months}",
        f"- Missing calendar months (gaps in continuity): {len(missing_months)}",
        f"- combined_index missing values: {index_missing}",
        f"- combined_inflation missing values: {inflation_missing}",
    ]
    if inflation_missing:
        early = gi[gi["combined_inflation"].isna()]["month"]
        lines.append(f"- Inflation missingness occurs in: {early.min().date()} -> {early.max().date()}"
                      f" (structural: YoY inflation needs the prior year's index, so early months of"
                      f" the series cannot have an inflation figure. NOT imputed.)")
    lines.append("")
    lines.append(f"Output written to: `{OUT.relative_to(OUT.parents[2])}`")
    write_log(LOG, lines)
    print(f"[CPI] General Index rows: {gi.shape[0]}, range {gi['month'].min().date()} -> {gi['month'].max().date()}")
    print(f"[CPI] index missing={index_missing}, inflation missing={inflation_missing}, dup months={dup_months}")
    return gi_out


if __name__ == "__main__":
    clean()
