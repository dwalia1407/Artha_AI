# HCES 2023-24 Processing Report

## Source structure
HCES 2023-24 is distributed as 15 CSV levels, each a different grain
(household roster, item-level food/non-food expenditure, durable goods,
etc.). This project uses Level 15 (household-visit consumption summary)
as the primary benchmark source, and inspects Level 14 (item-level
records) for the data inventory.

## Levels used
- Level 15: `LEVEL - 15 (Section 1_1, A2,B2  C2).csv`
- Level 14: `LEVEL - 14 (Section  A1,B1  C1).csv` (inspection only)

## Household key
Composite key (verified unique per household, 3 visit rows each): FSU_Serial_No, Sector, State, NSS_Region, District, Stratum, Sub_stratum, Panel, Sub_sample, FOD_Sub_Region, Sample_SU_No, Second_Stage_Stratum_No, Sample_Household_No

## Reference-period / weighting methodology actually applied
Level 15's MONTHLY_CONSUMPTION_EXP is NSSO's own pre-computed total monthly
consumption expenditure for a household for a given visit (already reference-
period-adjusted by NSSO, not re-derived here from item codes). Each household
is visited 3 times (sections A2, B2, C2) in different months across the survey
year. For per-capita benchmarking, each visit's MONTHLY_CONSUMPTION_EXP is first
divided by that visit's HOUSEHOLD_SIZE, and the three visit-level per-capita values
are then averaged. This avoids using a maximum household size as the denominator
when household composition changes across visits. The maximum reported household
size is retained only to assign the household-size group.

Weighted state x sector x household-size-group benchmarks use NSSO's
MULTIPLIER as the survey weight:

    weighted_mean = sum(consumption_pc * multiplier) / sum(multiplier)

## What was NOT attempted (and why)
Category-wise benchmarks (food_expense_pc, education_expense_pc,
medical_expense_pc, rent_expense_pc, etc.) as originally sketched in the
project context would require Level 14's ITEM_CODE to be mapped to named
categories and 7/30/365-day reference periods using the official NSSO
item-classification codebook. That codebook was not supplied with the raw
data. Reconstructing hundreds of item-code-to-category mappings from
memory risks fabricating definitions that are not actually verifiable -
which the project rules explicitly forbid. Level 14 is therefore only
profiled (row count, columns, missingness) for the data inventory, and no
category-level benchmark is produced from it in this submission.

## Validation performed
- Household uniqueness: verified (each household has exactly 3 A2/B2/C2 rows).
- MULTIPLIER consistency within a household: verified (0 households differ).
- HOUSEHOLD_SIZE consistency within a household: 2760 of 261953 households show a change across visits; maximum reported size is used only for household-size grouping, not as the per-capita denominator.
- Missing/invalid consumption values: 0 missing, 0 negative (none observed).

## Limitations
- Benchmarks are at state (numeric code) x sector x household-size-group
  grain, not city grain - HCES is not a city-level survey.
- No category-wise (food/education/medical/...) expenditure split is produced;
  only total household consumption expenditure per capita.
- State codes are the raw NSS numeric codes; no state-name lookup was supplied.
