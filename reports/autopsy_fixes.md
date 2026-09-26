# Artha AI — Post-Autopsy Fixes

This patch addresses the methodological and implementation issues identified during the project autopsy. Raw-source packaging/reproducibility is intentionally not addressed here because the project owner is adding the `data/raw/` sources separately.

## 1. Financial cash-flow semantics

`monthly_expenses` remains the recurring non-EMI expense total. `emi_amount` is treated separately as debt service.

The engineered definitions are now:

```text
disposable_income = monthly_income - monthly_expenses - emi_amount
monthly_savings   = disposable_income
```

This removes the previous inconsistency where `monthly_savings` ignored EMI while the synthetic source-level `savings` field included it.

`projected_savings` and the rule-derived `goal_feasibility` target therefore use post-expense, post-EMI cash surplus.

## 2. HCES per-capita aggregation

The HCES Level-15 processor now computes per-capita consumption at the visit level first:

```text
visit_consumption_pc = MONTHLY_CONSUMPTION_EXP / HOUSEHOLD_SIZE
```

The household benchmark value is then the mean of the three visit-level per-capita values. Maximum reported household size is retained only for household-size-group assignment.

This avoids using a maximum household size as the denominator for an average total consumption value when household composition changes across visits.

The corrected HCES processor will regenerate `hces_household_level.csv` and `hces_benchmarks.csv` when the raw HCES files are present and the full pipeline is rerun.

## 3. Synthetic randomness documentation

Documentation now correctly states that synthetic generation uses NumPy's explicit `default_rng(42)` generator rather than claiming use of the legacy global `np.random.seed()` API.

## 4. EDA interpretation

The EMI-ratio/savings-rate discussion now reports the measured correlation and explicitly identifies it as a generator-induced association rather than evidence of real-world causality.

The income/expense relationship remains explicitly described as a designed property of the synthetic generator.

## 5. Hidden QA

The independent hidden-QA formulas were updated to match the corrected post-EMI cash-flow definition. The regenerated hidden expected values match the actual `feature_engineering.engineer()` output with no mismatches.

## 6. Target and documentation refresh

All regenerated feature-engineering, validation, EDA, QA, and hidden-QA artifacts now reflect the corrected target distribution:

- Not feasible: 9,302
- Feasible: 698
- Feasible rate: 6.98%

No ML model was trained as part of this patch.
