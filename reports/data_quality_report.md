# Data Quality Report

Final dataset: `data/processed/final_user_dataset.csv`, shape (10000, 73)

## Schema validation
- all_required_columns_present: True
- missing_columns: []

## Identifier validation
- unique_user_ids: True
- valid_city_keys: True

## Range validation
- income_positive: True
- expenses_nonneg: True
- assets_nonneg: True
- liabilities_nonneg: True
- investments_nonneg: True
- family_size_ge1: True
- dependents_nonneg: True
- dependents_le_family_size: True
- goal_amount_nonneg: True
- goal_horizon_nonneg: True

## Date / continuity validation
- valid_reference_month: True
- cpi_monthly_continuity_gaps: 0
- rbi_monthly_continuity_gaps: 0

## Merge validation
- no_unexplained_user_loss: True
- no_row_multiplication: True

## Target validation (rule-derived goal_feasibility)
- target_values_valid_binary: True
- class_counts: {0: 9302, 1: 698}
- class_balance_pct: {0: 93.02, 1: 6.98}

## Missing data (final dataset, non-zero columns only)
- loan_interest_rate: 6001
- loan_tenure_years: 6001
- city_gdp_nominal_inr_billion: 8623
- city_ua_population_lakhs: 8623
- city_eol_score: 9566
- rbi_date: 5957

## Outlier analysis (IQR method, flagged not removed)
          column         q1         q3  iqr_lower_bound  iqr_upper_bound  n_below_lower  n_above_upper  pct_flagged
  monthly_income   21358.50   44039.25        -12662.62         78060.38              0            397         3.97
monthly_expenses   14823.00   28610.50         -5858.25         49291.75              0            313         3.13
 monthly_savings     719.25   16570.75        -23058.00         40348.00             69            256         3.25
      emi_amount       0.00    4377.50         -6566.25         10943.75              0            692         6.92
          assets  448202.00 1489975.00      -1114457.50       3052634.50              0            419         4.19
     liabilities       0.00  224693.00       -337039.50        561732.50              0           1208        12.08
     investments  132265.50  482225.00       -392673.75       1007164.25              0            413         4.13
     goal_amount 1583399.75 5007615.25      -3552923.50      10143938.50              0            421         4.21

Outliers are NOT automatically deleted. A high income, large asset base, or
large investment is plausible for a real household; this table exists to
surface extremes for review, not to justify silent trimming.

## Overall status: PASS
