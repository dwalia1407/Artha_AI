# HCES Processing Log

## Level 15 (household-visit summary)
- Raw shape: (1047812, 28)
- Households identified: 261953
- Households with inconsistent HOUSEHOLD_SIZE across visits (used max): 2760
- Households with missing household_monthly_consumption (all 3 visits null): 0
- Households with non-positive size: 0
- Households with negative consumption: 0

## Level 14 (item-level) - inspected only, not aggregated into a category benchmark
- Rows: 8296569
- Columns (22): ['Survey_Name', 'Year', 'FSU_Serial_No', 'Sector', 'State', 'NSS_Region', 'District', 'Stratum', 'Sub_stratum', 'Panel', 'Sub_sample', 'FOD_Sub_Region', 'Sample_SU_No', 'Sample_Sub_Division_No', 'Second_Stage_Stratum_No', 'Sample_Household_No', 'Questionnaire_No', 'Level', 'SECTION', 'ITEM_CODE', 'VALUE_RS', 'MULTIPLIER']
- Distinct ITEM_CODE values: 42
- VALUE_RS missing: 0
- No official item-classification codebook was supplied with the raw data, so ITEM_CODE
  values are NOT mapped to named categories (food/education/medical/etc.) in this submission.
  See reports/hces_processing.md for the full justification.

## Benchmark table (state x sector x household_size_group)
- Rows: 288
Output: data/processed/hces_household_level.csv (household grain, 261953 rows)
Output: data/processed/hces_benchmarks.csv (benchmark grain, 288 rows)
