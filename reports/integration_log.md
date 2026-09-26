# Integration Log

- User rows before integration: 10000
- Rows after all left-joins: 10000 (must equal 10000 - left joins on unique keys never multiply rows)

## USER + CITY
- city_master duplicate city_key: 0
- users unmatched to a city (should be 0, users were sampled from city_master): 0

## + CPI monthly
- cpi_monthly_clean duplicate month: 0
- users unmatched to a CPI month: 0

## + RBI monthly
- rbi_monthly_clean duplicate month: 0
- users unmatched to an RBI month: 0

## HCES benchmark - intentionally NOT joined here
Synthetic users carry a city, not an NSS state/sector code, and HCES benchmarks
are indexed by state x sector x household-size-group. Guessing a city->state
mapping to force a join would violate the project's 'never guess mappings' rule.
data/processed/hces_benchmarks.csv remains available as a standalone reference
table; joining it correctly is future work once users carry a genuine state field.

Output: `data/processed/final_user_dataset_integrated.csv`, shape (10000, 62)
