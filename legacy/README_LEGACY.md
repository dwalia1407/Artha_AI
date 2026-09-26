# Legacy Scripts (NOT used by the pipeline)

These are the original scripts from the uploaded `codes.zip`, kept here
for reference only. They were **not** run as part of this submission's
pipeline (`src/run_pipeline.py`) because inspection found problems that
would have violated the project's own non-negotiable rules:

- `02_clean_data.py` - filled missing numeric values with the column
  median and missing categoricals with `"unknown"` indiscriminately,
  including on fields where missingness is structural (e.g. CPI
  inflation, RBI SDF rate). This would have silently destroyed the
  structural-missingness signal the project explicitly requires
  preserving.
- `03.py` - assumed a raw file named `rbi_raw.xlsx` and a specific sheet
  structure that does not match the actual workbook
  (`Major Monetary Policy Rates...xlsx`, sheet `Report 1`), and
  forward-filled every column blindly rather than only the persistent
  policy-state columns.
- `merge_hces.py` - concatenated all 15 HCES levels into a single
  dataframe despite their different grains, and deleted the original
  raw files after processing (raw data must never be modified or
  deleted).
- `01_profile_data.py`, `utils.py` - generic profiling/utility helpers;
  not harmful, but superseded by `src/data_inspection.py` and
  `src/utils.py` in this submission, which are integrated with the
  rest of the pipeline's logging and validation conventions.

`src/cpi_processing.py`, `src/rbi_processing.py`, `src/hces_processing.py`
and `src/utils.py` were written fresh to fix these issues rather than
patching the legacy scripts, since the fixes touched their core logic.
