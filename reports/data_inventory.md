# Data Inventory

All figures below are measured from the actual files, not assumed.

## CPI - Rural, Urban, Combined.xlsx
- Sheet: CPI - 2012=100 (All India) (1)
- Grain: month x commodity (General Index subset used as monthly context)
- Role: monthly inflation/economic context
- See reports/cpi_processing_log.md for measured row counts and missingness.

## Major Monetary Policy Rates...xlsx
- Sheet: Report 1
- Grain: effective-date policy event (converted to monthly derived table)
- Role: monthly monetary-policy context
- See reports/rbi_processing_log.md for measured row counts and missingness.

## livingcost_india_all_inr (4).csv
- Shape: (221, 12)
- Columns: ['City', 'cost_one_person_usd', 'rent_one_person_usd', 'monthly_salary_after_tax_usd', 'income_after_rent_usd', 'months_covered', 'cost_one_person_inr', 'rent_one_person_inr', 'monthly_salary_after_tax_inr', 'income_after_rent_inr', 'usd_to_inr_rate_used', 'source_url']
- Missing cells: 0
- Duplicate rows: 0
- Grain: city. Role: primary city cost-of-living reference (221 cities).

## merged_cities_data (2).csv
- Shape: (30, 23)
- Columns: ['SL NO', 'city', 'gdp_nominal_inr_billion', 'ua_population_lakhs', 'eol_score', 'gdp_norm', 'pop_norm', 'eol_norm_filled', 'composite_score', 'justification', 'citations', 'matched_source_url_in_master', 'cost_one_person_usd', 'rent_one_person_usd', 'monthly_salary_after_tax_usd', 'income_after_rent_usd', 'months_covered', 'cost_one_person_inr', 'rent_one_person_inr', 'monthly_salary_after_tax_inr', 'income_after_rent_inr', 'usd_to_inr_rate_used', 'source_url']
- Missing cells by column (non-zero only): {'eol_score': 21, 'matched_source_url_in_master': 4}
- Duplicate rows: 0
- Grain: city (30 cities). Role: optional socioeconomic enrichment (gdp/population/eol).

## HCES 2023-24 (15 levels, `data/raw/HCES_Data_2023-24_Csv/`)
This project uses Level 15 as the primary benchmark source and inspects
Level 14 for the inventory; the other 13 levels are listed here for
completeness (row counts measured, not loaded/processed).

- `LEVEL - 01(Section 1 and 1_1).csv`: 261953 rows, 21 columns - not used in this submission
- `LEVEL - 02 (Section 3).csv`: 1107221 rows, 36 columns - not used in this submission
- `LEVEL - 03.csv`: 261953 rows, 40 columns - not used in this submission
- `LEVEL - 04 (Section 4_1).csv`: 261953 rows, 38 columns - not used in this submission
- `LEVEL - 05 ( Sec 5  6).csv`: 12754437 rows, 25 columns - not used in this submission
- `LEVEL - 06 (Section 7).csv`: 1757264 rows, 23 columns - not used in this submission
- `LEVEL - 07 (Section 4_2).csv`: 261953 rows, 47 columns - not used in this submission
- `LEVEL - 08 (Section 8_1).csv`: 1499971 rows, 25 columns - not used in this submission
- `LEVEL - 09 (Section 9  10  11).csv`: 8259120 rows, 21 columns - not used in this submission
- `LEVEL - 10 (Section 12).csv`: 829310 rows, 25 columns - not used in this submission
- `LEVEL - 11 (Section 4_3).csv`: 261953 rows, 59 columns - not used in this submission
- `LEVEL - 12 (Section 13).csv`: 4707351 rows, 22 columns - not used in this submission
- `LEVEL - 14 (Section  A1,B1  C1).csv`: 8296569 rows, 22 columns - INSPECTED ONLY (Level 14 - item-level, no codebook available)
- `LEVEL - 15 (Section 1_1, A2,B2  C2).csv`: 1047812 rows, 28 columns - USED (Level 15 - household benchmark)
- `Level - 13 (Section 14).csv`: 4951749 rows, 27 columns - not used in this submission

## Synthetic user financial data
- Grain: individual user x reference month
- Generated (not sourced): see reports/user_generation_log.md for the full
  generation methodology, assumptions, and validation results.

