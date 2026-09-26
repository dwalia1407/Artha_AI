# Data Preprocessing Report - Artha AI FMS

## 1. Project Overview
Artha AI is a data-driven financial management system. This submission
implements its complete data foundation: acquisition/cleaning of
economic context (CPI, RBI), city cost-of-living context, HCES 2023-24
household expenditure benchmarks, a synthetic user financial population,
their integration, feature engineering, validation, and EDA. **ML model
training is explicitly out of scope for this submission** (see Section
16 and `reports/ml_methodology_plan.md`).

## 2. Dataset Inventory
Full measured inventory (rows, columns, missingness, duplicates) for
every raw source: `reports/data_inventory.md`. Summary:

| Dataset | Grain | Rows (measured) | Role |
|---|---|---|---|
| CPI (General Index) | month | 156 | monthly inflation context |
| RBI monthly | month | 156 | monthly monetary-policy context |
| LivingCost | city | 221 | primary city cost-of-living reference |
| 30-city enrichment | city | 30 | optional GDP/population/EOL enrichment |
| HCES Level 15 | household-visit | 1,047,812 rows -> 261,953 households | consumption benchmark source |
| HCES Level 14 | item-level | 8,296,569 | inspected only, not aggregated |
| Synthetic users | user x month | 10,000 | central personalized profile |

## 3. Data Grain and Integration Strategy
Final modelling grain: **one user + one reference month + one city**.
CPI and RBI are joined on `reference_month`; city context on `city_key`.
HCES benchmarks (state x sector x household-size-group) are NOT joined
at user level in this submission because synthetic users do not carry a
genuine state/sector field - see Section 7 and `reports/integration_log.md`.

## 4. CPI Preprocessing
Source: `CPI - Rural, Urban, Combined.xlsx`, sheet
`CPI - 2012=100 (All India) (1)`. A real bug was found and fixed during
processing: the sheet carries both a "Provisional" and a later "Final"
release for the same month once finalized, which initially produced 130
duplicate-month rows; these are collapsed to one row per month
(preferring Final). Result: 156 General Index rows, Jan 2013 - Dec 2025,
0 duplicate months, 0 missing calendar months, 0 missing index values,
12 missing inflation values (Jan-Dec 2013 - structurally unavoidable,
since YoY inflation needs the prior year's index; left missing, not
imputed). Full log: `reports/cpi_processing_log.md`.

## 5. RBI Preprocessing
Source: `Major Monetary Policy Rates and Reserve Requirements...xlsx`,
sheet `Report 1`. Effective-date events cleaned (259 rows, `-`
placeholders converted to missing, never to 0), then converted to a
monthly table via domain-based state propagation: each month takes the
actual final effective observation within that month, and persistent
policy variables are forward-filled to represent "no change this month"
(not statistical imputation). Result: 156 monthly rows; missingness
matches the structural expectation (sdf_rate: 111 missing before SDF
existed, crr: 1, slr: 17, all left missing). Full log:
`reports/rbi_processing_log.md`.

## 6. City Data Integration
LivingCost (221 cities) used as the base reference. The 30-city
socioeconomic dataset only contributes genuinely new fields
(gdp_nominal_inr_billion, ua_population_lakhs, eol_score) -
composite_score and its normalized inputs are deliberately excluded as
redundant. Two of 30 cities ("hyderabad", "kochi") did not exact-match
the 221-city key; inspection showed the 221-city file carries these as
"Hyderabad, Telangana" and "Kochi, Kerala" - an explicit, inspected
mapping was applied (not guessed). Final: 30/30 matched,
`validate="one_to_one"` merge, 221-row master unchanged in row count.
Full log: `reports/city_processing_log.md`.

## 7. HCES 2023-24 Processing
Level 15 (household-visit summary) is the primary source: each household
(261,953, verified unique by a 13-field composite key) has 3 seasonal
visit rows (A2/B2/C2); household consumption is the mean of the three
visits' MONTHLY_CONSUMPTION_EXP (NSSO's own pre-computed totals, not
re-derived from item codes). A weighted (MULTIPLIER) per-capita
benchmark was built at state x sector x household-size-group grain (288
rows). **Category-wise benchmarks (food/education/medical/etc.) were
NOT built**: Level 14 (8,296,569 item-level rows, 42 distinct ITEM_CODE
values) has no category/description field, and no official NSSO
item-classification codebook was supplied with the raw data; mapping
codes to categories from memory would risk fabricating definitions,
which the project rules explicitly forbid. This is documented, not
silently skipped. Full methodology: `reports/hces_processing.md`.

## 8. Household Services
Represented in the synthetic user generator as
`service_type x usage_flag x assumed_monthly_rate`, using explicitly
labeled synthetic assumptions (not sourced market pricing):
cleaning=Rs1500, cooking=Rs4000, dishwashing=Rs800, laundry=Rs1000 per
month, with usage probability increasing with income. See
`src/user_generation.py` and `reports/user_generation_log.md`.

## 9. Synthetic User Data
10,000 users generated with NumPy's explicit `default_rng(42)`, income and rent
grounded in the real `city_master` cost-of-living figures (sampled city
determines the base), expense buckets as documented income fractions
with noise. All 12 generation-time validation checks passed (unique IDs,
positive income, dependents <= family size, valid city reference, etc.).
Explicitly labeled synthetic throughout every report that references it.
Full log: `reports/user_generation_log.md`.

## 10. Data Integration
User + City + CPI(month) + RBI(month): 10,000 rows in, 10,000 rows out,
0 unmatched on any of the three joins, all merges validated
(`validate="many_to_one"`). HCES intentionally not joined at user level
(Section 7 / Section 3). Full log: `reports/integration_log.md`.

## 11. Feature Engineering
disposable_income, monthly_savings (post-expense, post-EMI cash surplus), savings_rate, emi_ratio, rent_burden,
net_worth, household_service_expense_ratio, goal_horizon_years,
future_goal_cost (`ANNUAL_INFLATION_ASSUMPTION = 0.05`, an explicit
planning assumption, not observed CPI inflation and not used to fill any
missing value), and the rule-derived `goal_feasibility` target (class
counts: 9,302 not-feasible / 698 feasible in this synthetic population -
**deterministically computed from the row's own inputs, not a real-world
observed outcome**). Full log: `reports/feature_engineering_log.md`.

## 12. Missing-Data Strategy
Every missingness source was classified before treatment:
- **Structural** (CPI inflation Jan-Dec 2013, RBI SDF before
  introduction) - left missing, never imputed.
- **State/event absence** (RBI months with no policy change) -
  forward-filled as domain-justified state propagation, not statistical
  imputation.
- **City enrichment gaps** (eol_score missing for 21 of 30 cities in the
  source) - left missing, not filled.
No `fillna(0)`, mean-fill, or blanket forward-fill was used anywhere in
this pipeline.

## 13. Data Validation
Automated schema, identifier, range, date/continuity, merge, and target
checks - all passing (`reports/data_quality_report.md`). Final dataset
missingness is limited to columns that are genuinely optional/context-
dependent (e.g. `loan_interest_rate`/`loan_tenure_years` for the 6,001
users without a loan; `city_eol_score` for cities the 30-city dataset
does not cover; `rbi_date` for months with no policy change - all
expected, all explained).

## 14. Outlier Analysis
IQR-based flagging on 8 financial variables (income, expenses, savings,
EMI, assets, liabilities, investments, goal amount) -
`results/tables/outlier_summary.csv`. Flag rates range from ~3% (income,
expenses) to ~12% (liabilities). Nothing was deleted; a high income or
asset value is a plausible real household, not necessarily an error.

## 15. Exploratory Data Analysis
15 plots (`results/eda/01_*.png` - `15_*.png`) covering univariate
distributions, income/expense/savings relationships, CPI/RBI trends over
time, the target's class distribution, and city/HCES comparisons.
Descriptive statistics: `results/tables/eda_descriptive_stats.csv`.
Narrative with observations and limitations: `reports/eda_report.md`.

## 16. Data Splitting & Methodology Planning
70/15/15 train/validation/test proposed, `random_state=42`, with
explicit leakage-prevention rules (fit-on-train-only preprocessing, no
duplicate users across splits, no target-derived predictors). Full plan:
`reports/ml_methodology_plan.md`.

## 17. Project Scope & Future ML Plan
Proposed models (Logistic Regression, Random Forest), planned evaluation
metrics, cross-validation, hyperparameter tuning, interpretability, and
real-world-validation requirements are all specified but **not
executed** - see `reports/ml_methodology_plan.md` Sections 4-11.

## 18. Limitations
- Synthetic users are not real customers and must not be presented as
  such.
- `goal_feasibility` is rule-derived, not an observed outcome.
- No HCES category-level (food/education/medical) benchmark - codebook
  unavailable (Section 7).
- HCES benchmarks are not joined to individual users (Section 3/10).
- City-level cost figures reflect the LivingCost dataset's own point
  estimates, not an independently re-verified source.
- State codes in HCES benchmarks are raw NSS numeric codes; no
  state-name lookup table was supplied.

## 19. Reproducibility
All synthetic randomness uses NumPy's explicit `default_rng(42)` generator. All
paths are relative (`pathlib`-based, see `src/utils.py`). Single
entry point:
```
python3 src/run_pipeline.py
```
run from the project root (`Artha_AI/`). Re-running it regenerates every
processed file, report, table, and plot referenced in this document from
the raw sources in `data/raw/`, deterministically.

## 20. Final Status
The data acquisition, cleaning, integration, feature engineering,
validation, and EDA layers are implemented, executed, and validated with
real, measured numbers throughout - see every log/report cited above.
**The ML component is fully specified as a future implementation plan
and was not trained; no ML accuracy, precision, recall, F1, ROC-AUC, or
confusion matrix appears anywhere in this project.**
