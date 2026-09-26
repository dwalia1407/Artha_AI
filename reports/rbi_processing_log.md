# RBI Processing Log

- Source workbook sheet: `Report 1`
- Raw candidate data rows: 261
- Rows with invalid/unparsable date (dropped): 2
- Duplicate effective dates (dropped, kept first): 0
- Clean event-level rows: 259
- Coverage: 1935-07-05 -> 2025-12-05
- Output: `data/processed/rbi_rates_clean.csv`

## Monthly derived table (Jan 2013 - Dec 2025)
- Rows: 156
  - missing `month`: 0
  - missing `date`: 103
  - missing `bank_rate`: 0
  - missing `repo_rate`: 0
  - missing `reverse_repo_rate`: 0
  - missing `sdf_rate`: 111
  - missing `msf_rate`: 0
  - missing `crr`: 1
  - missing `slr`: 17

Interpretation:
- `date` missing = no policy change was effective that month (state carried forward).
- `sdf_rate` missingness reflects the period before the Standing Deposit Facility existed.
- Early `crr`/`slr` gaps reflect periods this workbook does not report a change for; values
  are left missing rather than invented.

Output: `data/processed/rbi_monthly_clean.csv`
