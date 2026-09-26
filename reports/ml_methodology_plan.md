# ML Methodology Plan (FUTURE IMPLEMENTATION - NOT TRAINED IN THIS SUBMISSION)

This document specifies how the future ML component of Artha AI would be
built. **No model in this document has been trained.** No accuracy,
precision, recall, F1, ROC-AUC, or confusion matrix appears anywhere in
this project, because none was computed. This is intentional and matches
the current academic rubric, which asks for methodology planning, not a
trained model.

## 1. Problem definition

Binary classification: predict `goal_feasibility` - whether a user's
stated financial goal is likely to be met given their financial profile
and horizon.

**Current status of the target**: `goal_feasibility` in this project's
final dataset is a RULE-DERIVED / SYNTHETIC target,
deterministically computed as:

```
projected_savings = monthly_savings * 12 * goal_horizon_years + investments
goal_feasibility = projected_savings >= future_goal_cost
```

A model trained on this target today would mostly learn to reproduce the
rule above from its own inputs - it would not demonstrate real-world
predictive power. Before any real training, the target should be
replaced by (or validated against) an observed outcome, e.g. whether a
user's goal was actually met by the target date, if such longitudinal
data becomes available.

## 2. Candidate inputs

age, monthly_income, monthly_expenses, monthly_savings, savings_rate,
emi_amount, emi_ratio, rent_burden, assets, liabilities, investments,
net_worth, dependents, family_size, city context (cost/rent/salary,
gdp/population/eol where available), CPI monthly context, RBI monthly
context, goal_horizon_years, future_goal_cost, household_service_expense
ratio. (HCES benchmark context is not yet joined at user level - see
`integration_log.md` - and is therefore not a candidate input until a
genuine user state/sector field exists.)

## 3. Data splitting strategy

Proposed split: **70% train / 15% validation / 15% test**, with
`random_state=42`.

- **Training set**: fits the future model and any learned preprocessing
  (imputers, encoders, scalers).
- **Validation set**: model selection and hyperparameter tuning.
- **Test set**: touched exactly once, for final unbiased evaluation.

Because the current dataset is synthetic and constant-date (not a real
longitudinal panel), a random split is acceptable for demonstrating the
methodology. **For real-world longitudinal financial data, a temporal
split (train on earlier periods, validate/test on later periods) would
be preferable**, to avoid leaking future information into training and
to test genuine forecasting ability.

Leakage-prevention rules the future implementation must follow:
- `projected_savings`, `goal_feasibility`, and any direct deterministic component used to construct the current synthetic target must not be used as predictors for that target.
- Fit all preprocessing (imputation, encoding, scaling) on the training
  split only; transform validation/test with the fitted objects.
- No target-derived quantity may appear among the predictors.
- No duplicate user should appear across splits.
- Use `sklearn.pipeline.Pipeline` / `ColumnTransformer` so fit/transform
  boundaries are enforced by construction rather than by discipline.

## 4. Proposed algorithms (NOT trained here)

**Model 1 - Logistic Regression**: interpretable baseline, coefficients
give directional interpretation, appropriate for a binary target.

**Model 2 - Random Forest**: captures nonlinear relationships and
feature interactions, robust baseline, does not require feature scaling,
useful comparison against the linear model.

No other algorithms are added merely to inflate the model list.

## 5. Future preprocessing strategy

- Numerical features: validate ranges, impute only where an accidental
  (not structural) missing value is identified; scale only for the
  Logistic Regression path (Random Forest does not need it).
- Categorical features (financial_goal, risk_tolerance, city,
  employment-type-like fields): one-hot encode via a training-fitted
  encoder. Ordinal encoding is reserved for genuinely ordered categories.
- All of the above wrapped in a `ColumnTransformer` inside a `Pipeline`
  fitted only on the training split.

## 6. Class imbalance

Current rule-derived target distribution (measured, not assumed): see
`feature_engineering_log.md` for the exact class counts and rate. No
balancing technique has been applied. Future options, to be chosen only
after seeing the real target's balance: stratified splitting, class
weights, thresholded decision rules; oversampling would only be
considered with clear evidence of a problematic imbalance, not by
default.

## 7. Evaluation strategy (metrics NOT computed in this submission)

The future implementation would report, on the validation set during
development and the test set once at the end:
- **Accuracy** - can mislead under class imbalance.
- **Precision** - relevant if a false "feasible" recommendation is costly.
- **Recall** - relevant if missing a genuinely (in)feasible case is costly.
- **F1** - balances precision and recall.
- **ROC-AUC** - ranking/discrimination across thresholds.

## 8. Cross-validation (NOT executed in this submission)

Planned: stratified k-fold cross-validation on the training split only,
for model selection; the test split stays untouched until final
evaluation. If/when the data becomes genuinely temporal, ordinary random
k-fold would be replaced with a time-aware validation scheme (e.g.
expanding-window backtesting).

## 9. Hyperparameter tuning (NOT performed in this submission)

- Logistic Regression: regularization strength (C), solver.
- Random Forest: number of trees, max depth, min samples per split/leaf,
  feature sampling fraction.
Tuning would use cross-validation on the training split only, never the
test split.

## 10. Interpretability (planned, not executed)

- Logistic Regression: coefficient sign/magnitude analysis.
- Random Forest: feature importances, with the explicit caveat that
  importance is not causality - a feature mattering to the model does
  not mean it causes the financial outcome.

## 11. Real-world validation requirements (future work)

This project does not, and cannot yet, establish real-world predictive
performance, because its target is rule-derived and its user population
is synthetic. Genuine future validation would require: real financial
records collected with appropriate consent and legal basis, an observed
ground-truth outcome (not a formula), temporal out-of-sample testing,
external validation on an independent population, calibration checks,
and subgroup performance review (e.g. by income band, age group,
household size, urban/rural) without making fairness claims the data
cannot support.
