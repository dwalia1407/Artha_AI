# CPI Processing Log

- Source workbook sheet: `CPI - 2012=100 (All India) (1)`
- Header row located at raw row index: 5
- Raw data rows after header slice (before cleaning): 7969
- Rows dropped for unparsable month/commodity: n/a (dropna on month/commodity applied first)
- Rows with unparsable month value (dropped): 0
- Exact duplicate rows removed: 0
- Cleaned full table shape (all commodities): (7969, 9)

## General Index monthly series
- Raw General Index rows before Provisional/Final dedup: 286
- Duplicate (Provisional+Final) month rows collapsed: 130 (kept Final where available, else Provisional)
- Rows: 156
- Date range: 2013-01-01 -> 2025-12-01
- Duplicate months in General Index series: 0
- Missing calendar months (gaps in continuity): 0
- combined_index missing values: 0
- combined_inflation missing values: 12
- Inflation missingness occurs in: 2013-01-01 -> 2013-12-01 (structural: YoY inflation needs the prior year's index, so early months of the series cannot have an inflation figure. NOT imputed.)

Output written to: `data/processed/cpi_monthly_clean.csv`
