# Presentation Content

## Slide 1 - Title
Artha AI - AI-Based Financial Management System
Data Foundation, Preprocessing & EDA (Current Submission Scope)

## Slide 2 - Problem Statement
Individuals need financial guidance that accounts for their own profile
*and* their economic context (inflation, monetary policy, city cost of
living, household expenditure norms) - not generic rules of thumb.
Artha AI's data foundation brings these sources together at a
user-month-city grain.

## Slide 3 - Objectives
- Build a clean, traceable, domain-correct data pipeline (CPI, RBI,
  city, HCES, synthetic user data).
- Engineer defensible financial features.
- Validate everything, including structural vs accidental missingness.
- Run genuine EDA.
- Specify (not train) the future ML methodology.

## Slide 4 - System Architecture
RAW DATA -> per-source cleaning (CPI/RBI/City/HCES) -> synthetic user
generation -> integration (user+city+CPI+RBI) -> feature engineering ->
validation -> EDA -> QA -> future ML plan.
See `README.md` "Architecture" for the full diagram.

## Slide 5 - Dataset Overview
- CPI: 156 monthly General Index rows, Jan 2013-Dec 2025.
- RBI: 259 policy events -> 156 monthly rows.
- City: 221-city cost-of-living master + 30-city GDP/population/EOL enrichment.
- HCES: 15-level survey; Level 15 used (261,953 households), Level 14
  inspected only (8.3M item-level rows, no codebook available).
- Synthetic users: 10,000 rows, seed 42.

## Slide 6 - Data Understanding
Every number on this slide is measured, not assumed - see
`reports/data_inventory.md` for the full per-file profile (rows,
columns, missingness, duplicates) of every raw source actually used.

## Slide 7 - Data Preprocessing
- CPI: resolved a Provisional/Final duplicate-month issue; kept
  structural inflation missingness (Jan-Dec 2013) un-imputed.
- RBI: effective-date events correctly converted to a monthly series via
  domain-based state propagation (not blind forward-fill); "-" kept as
  missing, never coerced to 0.
- City: 30/30 cities matched via one inspected explicit mapping
  (Hyderabad, Kochi), validated one-to-one.

## Slide 8 - HCES Methodology
Level 15 household-visit records are converted to visit-level per-capita
consumption, averaged across 3 visits, then weighted (MULTIPLIER) into a
state x sector x household-size-group per-capita benchmark (288 rows).
Maximum reported household size is used only for size-group assignment.
Category-level breakdown (food/education/medical) intentionally NOT
attempted - no official item-classification codebook was available, and
guessing one would mean fabricating category definitions.

## Slide 9 - Data Integration
User + City + CPI(month) + RBI(month), all left-joins validated
one-to-one / many-to-one, 10,000 rows in -> 10,000 rows out, zero
unmatched. HCES intentionally not joined at user level (no state/sector
field on synthetic users) - documented, not forced.

## Slide 10 - EDA
15 plots covering univariate distributions, income/expense/savings
relationships, CPI/RBI trends, target distribution, and city/HCES
comparisons. See `results/eda/` and `reports/eda_report.md`.

## Slide 11 - Feature Engineering
disposable_income, monthly_savings (post-expense, post-EMI cash surplus),
savings_rate, emi_ratio, rent_burden, net_worth, goal_horizon_years, future_goal_cost (5% planning assumption,
not observed inflation), and a rule-derived goal_feasibility target
(explicitly not real-world ground truth).

## Slide 12 - Data Splitting & Methodology Planning
70/15/15 train/validation/test, random_state=42, leakage-prevention
rules, proposed models (Logistic Regression, Random Forest) - planning
only, nothing trained. See `reports/ml_methodology_plan.md`.

## Slide 13 - Future ML Methodology
Evaluation metrics, cross-validation strategy, hyperparameter tuning
plan, interpretability plan, real-world validation requirements - all
specified, none executed. See `reports/ml_methodology_plan.md`
Sections 7-11.

## Slide 14 - Data Validation & QA
`reports/data_quality_report.md` (schema/range/merge/target checks, all
passing), `reports/test_cases.md` (20/20 pipeline test cases passing,
run against real code), `reports/hidden_qa_log.md` (independent
cross-check, all matched).

## Slide 15 - Limitations
Synthetic users are not real customers; the goal_feasibility target is
rule-derived, not observed; HCES category breakdown and user-level HCES
join are out of scope for this submission (documented reasons on Slide 8
/ Slide 9).

## Slide 16 - Future Scope
Replace the rule-derived target with an observed outcome; obtain the
official HCES item-classification codebook for category-level
benchmarks; add a genuine user state/sector field to join HCES
properly; then execute the ML plan in `reports/ml_methodology_plan.md`.

## Slide 17 - Team Contributions
See `reports/team_contributions.md`.

## Slide 18 - Conclusion
The data/preprocessing/EDA foundation is implemented and validated end
to end with real, executed numbers throughout. The ML component is
fully specified as a future implementation plan; no model was trained
and no ML metric appears anywhere in this project.
