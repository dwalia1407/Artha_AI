"""
RBI monetary policy rate processing.

Source workbook: data/raw/Major Monetary Policy Rates and Reserve
Requirements - Bank Rate, LAF (Repo, Reverse Repo, SDF and MSF) Rates,
CRR & SLR.xlsx
Sheet: "Report 1"

The sheet has a report header, then a two-row merged column header,
then a numbered "1,2,3..." spacer row, then the actual data rows,
newest date first.

Outputs:
  data/processed/rbi_rates_clean.csv   (effective-date event table)
  data/processed/rbi_monthly_clean.csv (monthly derived table, Jan2013-Dec2025)
"""

import pandas as pd
from utils import RAW_DIR, PROCESSED_DIR, REPORTS_DIR, write_log

SRC = RAW_DIR / "Major Monetary Policy Rates and Reserve Requirements - Bank Rate, LAF (Repo, Reverse Repo, SDF and MSF) Rates, CRR & SLR.xlsx"
SHEET = "Report 1"
OUT_EVENTS = PROCESSED_DIR / "rbi_rates_clean.csv"
OUT_MONTHLY = PROCESSED_DIR / "rbi_monthly_clean.csv"
LOG = REPORTS_DIR / "rbi_processing_log.md"

COLS = ["date", "bank_rate", "repo_rate", "reverse_repo_rate",
        "sdf_rate", "msf_rate", "crr", "slr"]


def find_header_and_data_start(raw: pd.DataFrame):
    header_row = None
    for i in range(min(15, len(raw))):
        row_vals = raw.iloc[i].fillna("").astype(str).str.strip().tolist()
        if "Effective Date" in "".join(row_vals):
            header_row = i
            break
    if header_row is None:
        raise ValueError("Could not find 'Effective Date' header row")
    # The row right after the header block is a "1,2,3..." spacer row.
    data_start = header_row + 2
    while True:
        first_cell = str(raw.iloc[data_start, 1]).strip()
        if first_cell in {"1", "nan", ""}:
            data_start += 1
        else:
            break
    return header_row, data_start


def clean_events():
    raw = pd.read_excel(SRC, sheet_name=SHEET, header=None)
    header_row, data_start = find_header_and_data_start(raw)

    data = raw.iloc[data_start:, 1:9].copy()
    data.columns = COLS
    raw_rows = data.shape[0]

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    invalid_dates = data["date"].isna().sum()
    data = data.dropna(subset=["date"])

    # Critical rule: '-' is a placeholder for "not applicable / no change
    # reported", not zero. Convert to NaN, never to 0.
    for col in COLS[1:]:
        data[col] = data[col].replace("-", pd.NA)
        data[col] = pd.to_numeric(data[col], errors="coerce")

    dup_dates = data["date"].duplicated().sum()
    data = data.drop_duplicates(subset="date")

    data = data.sort_values("date").reset_index(drop=True)
    data.to_csv(OUT_EVENTS, index=False)

    return data, {
        "raw_rows": raw_rows,
        "invalid_dates_dropped": int(invalid_dates),
        "duplicate_effective_dates": int(dup_dates),
        "clean_rows": data.shape[0],
        "coverage_start": data["date"].min(),
        "coverage_end": data["date"].max(),
    }


def to_monthly(events: pd.DataFrame):
    """
    RBI is an effective-date EVENT table, not a monthly observation table.
    A rate stays in force until the next change. We build a full monthly
    calendar and, for each month, take the actual final effective
    observation within that month (an event row, not a per-column
    last-non-null blend across different rows), then forward-fill each
    persistent policy variable across months with no change.
    """
    start, end = pd.Timestamp("2013-01-01"), pd.Timestamp("2025-12-01")
    calendar = pd.DataFrame({"cal_month": pd.date_range(start, end, freq="MS")})

    ev = events.copy()
    ev["cal_month"] = ev["date"].values.astype("datetime64[M]")

    # For months with more than one policy change, keep the single row
    # with the latest effective date in that month (the true final state).
    ev_last_per_month = (
        ev.sort_values("date")
        .groupby("cal_month", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    monthly = calendar.merge(
        ev_last_per_month[["cal_month", "date"] + COLS[1:]],
        on="cal_month", how="left", validate="one_to_one",
    )

    # Domain-based state propagation: a policy rate holds until it is
    # next changed. This is NOT statistical imputation of missing data;
    # it encodes "no change was announced this month".
    persistent_cols = ["bank_rate", "repo_rate", "reverse_repo_rate",
                        "sdf_rate", "msf_rate", "crr", "slr"]
    for col in persistent_cols:
        monthly[col] = monthly[col].ffill()

    monthly = monthly.rename(columns={"cal_month": "month"})
    monthly.to_csv(OUT_MONTHLY, index=False)
    return monthly


def clean():
    events, stats = clean_events()
    monthly = to_monthly(events)

    monthly_missing = monthly.isna().sum()

    lines = [
        "# RBI Processing Log",
        "",
        f"- Source workbook sheet: `{SHEET}`",
        f"- Raw candidate data rows: {stats['raw_rows']}",
        f"- Rows with invalid/unparsable date (dropped): {stats['invalid_dates_dropped']}",
        f"- Duplicate effective dates (dropped, kept first): {stats['duplicate_effective_dates']}",
        f"- Clean event-level rows: {stats['clean_rows']}",
        f"- Coverage: {stats['coverage_start'].date()} -> {stats['coverage_end'].date()}",
        f"- Output: `data/processed/rbi_rates_clean.csv`",
        "",
        "## Monthly derived table (Jan 2013 - Dec 2025)",
        f"- Rows: {monthly.shape[0]}",
    ]
    for col in ["date"] + persistent_note(monthly):
        pass
    for col, val in monthly_missing.items():
        lines.append(f"  - missing `{col}`: {val}")
    lines += [
        "",
        "Interpretation:",
        "- `date` missing = no policy change was effective that month (state carried forward).",
        "- `sdf_rate` missingness reflects the period before the Standing Deposit Facility existed.",
        "- Early `crr`/`slr` gaps reflect periods this workbook does not report a change for; values",
        "  are left missing rather than invented.",
        "",
        f"Output: `data/processed/rbi_monthly_clean.csv`",
    ]
    write_log(LOG, lines)
    print(f"[RBI] event rows={stats['clean_rows']}, monthly rows={monthly.shape[0]}")
    print(monthly_missing.to_dict())
    return events, monthly


def persistent_note(monthly):
    return [c for c in monthly.columns if c != "month"]


if __name__ == "__main__":
    clean()
