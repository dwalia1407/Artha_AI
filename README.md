# Artha AI - AI-Based Financial Management System

## Problem Statement
Individuals need financial guidance that accounts for their own profile
*and* the economic context around them - inflation, monetary policy,
city cost of living, and household expenditure norms - not generic
rules of thumb. Artha AI's current scope builds the complete, validated
data foundation this requires.

## Objectives
1. Correctly understand and clean each economic/contextual data source.
2. Build a synthetic user financial population for pipeline development.
3. Integrate user + city + CPI + RBI context at a defensible grain.
4. Engineer transparent financial features and a rule-derived planning
   target.
5. Validate every stage and run genuine EDA.
6. Fully specify (but not train) the future ML methodology.

**ML model training is explicitly out of scope for this submission.**
See `reports/ml_methodology_plan.md`.

## Architecture
```
RAW DATA
   |
   +-- CPI (xlsx) -----------> cpi_monthly_clean.csv
   +-- RBI (xlsx) -----------> rbi_rates_clean.csv, rbi_monthly_clean.csv
   +-- LivingCost + 30-city -> city_master.csv
   +-- HCES Level 15/14 -----> hces_household_level.csv, hces_benchmarks.csv
   |
SYNTHETIC USER GENERATION (10,000 users, seed=42) -> user_financial_data.csv
   |
INTEGRATION (user + city + CPI + RBI, validated joins) -> final_user_dataset_integrated.csv
   |
FEATURE ENGINEERING (ratios, rule-derived target) -> final_user_dataset.csv
   |
VALIDATION -> reports/data_quality_report.md
   |
EDA -> results/eda/*.png, reports/eda_report.md
   |
PIPELINE QA + HIDDEN QA -> reports/test_cases.md, reports/hidden_qa_log.md
   |
FUTURE ML METHODOLOGY (planned, not executed) -> reports/ml_methodology_plan.md
```

## Datasets
| Dataset | Source file | Grain | Role |
|---|---|---|---|
| CPI | `CPI - Rural, Urban, Combined.xlsx` | month | inflation context |
| RBI | `Major Monetary Policy Rates...xlsx` | effective-date event -> month | monetary-policy context |
| City | `livingcost_india_all_inr (4).csv` + `merged_cities_data (2).csv` | city | cost-of-living / socioeconomic context |
| HCES 2023-24 | `HCES_Data_2023-24_Csv/LEVEL - 15...csv` (+ Level 14 inspected) | household-visit | consumption benchmark |
| Synthetic users | generated | user x month | central financial profile |

## Preprocessing highlights
- CPI: fixed a Provisional/Final duplicate-month bug; kept 12 months of
  structural inflation missingness un-imputed.
- RBI: `-` placeholders kept as missing (never coerced to 0); monthly
  series built by domain-based policy-state propagation, not blind
  forward-fill.
- City: Hyderabad/Kochi name mismatch resolved via an inspected, explicit
  mapping (not a guess).
- HCES: household-level consumption benchmark built from real Level 15
  data; category-level (food/education/etc.) breakdown intentionally
  NOT attempted - no official item-classification codebook was supplied.

See `reports/data_preprocessing_report.md` for the full 20-section
report and `reports/rubric_mapping.md` for how every rubric section maps
to generated evidence.

## HCES Methodology
See `reports/hces_processing.md` for the full household-key
identification, reference-period handling, and weighting methodology,
including an explicit statement of what was and was not attempted and
why.

## Feature Engineering
`disposable_income`, `monthly_savings`, `savings_rate`, `emi_ratio`,
`rent_burden`, `net_worth`, `household_service_expense_ratio`,
`goal_horizon_years`, `future_goal_cost` (5% planning assumption, not
observed inflation), and a `goal_feasibility` target that is explicitly
**rule-derived / synthetic, not a real-world observed outcome**.

## EDA
15 plots in `results/eda/`, descriptive statistics in
`results/tables/eda_descriptive_stats.csv`, full narrative in
`reports/eda_report.md`.

## Data Validation
`reports/data_quality_report.md` - schema, identifier, range,
date/continuity, merge, and target checks, plus IQR outlier flagging
(flagged, never silently deleted).

## Data Splitting Plan
70% train / 15% validation / 15% test, `random_state=42`, with explicit
leakage-prevention rules. See `reports/ml_methodology_plan.md`.

## Future ML Methodology
Fully specified, **not executed**: proposed models (Logistic Regression,
Random Forest), planned evaluation metrics, cross-validation,
hyperparameter tuning, interpretability, and real-world validation
requirements. No ML metric appears anywhere in this project. See
`reports/ml_methodology_plan.md`.

## Limitations
- All user data is synthetic; not real customers.
- `goal_feasibility` is a deterministic rule, not an observed outcome.
- No HCES category-level expenditure benchmark (codebook unavailable).
- HCES benchmarks are not joined to individual users (no genuine
  state/sector field on synthetic users).
- This project does not establish real-world predictive performance.

## Project Structure
```
Artha_AI/
├── data/
│   ├── raw/            (original sources, never modified)
│   ├── processed/       (every cleaned/derived table)
│   └── hidden/          (hidden QA input/expected pairs)
├── src/                 (one script per pipeline stage + run_pipeline.py)
├── results/
│   ├── eda/              (15 plots)
│   ├── tables/            (descriptive stats, outlier summary, QA summary, quality summary)
│   └── data_pipeline_qa.csv
├── reports/              (one .md report per stage, plus the master report)
├── presentation/
│   └── presentation_content.md
├── legacy/               (original uploaded scripts, NOT used - see README_LEGACY.md)
├── README.md
└── requirements.txt
```

## Financial feature definition

`monthly_expenses` represents recurring non-EMI expenses. Debt service is
represented separately by `emi_amount`; therefore engineered `monthly_savings`
and `disposable_income` are both defined as `monthly_income - monthly_expenses - emi_amount`.
This post-EMI surplus is the cash-flow basis used by the rule-derived
`goal_feasibility` target.

## Reproducibility
```
pip install -r requirements.txt
python3 src/run_pipeline.py
```
Run from the project root. All synthetic randomness uses NumPy's explicit `default_rng(42)` generator. All paths are relative.
Re-running regenerates every processed file, report, table, and plot
from the raw sources in `data/raw/` deterministically. No ML training
step exists to run.

## Final Status
Data acquisition, cleaning, integration, feature engineering, validation,
and EDA are implemented, executed, and validated end to end with real,
measured numbers throughout. **The ML component is fully specified as a
future implementation plan and was not trained as part of this
submission.**
