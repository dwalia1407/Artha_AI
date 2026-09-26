# Synthetic User Data Generation Log

- Users generated: 10000 (target: 10000)
- Seed: 42
- Explicitly synthetic: grounded in real city_master cost-of-living figures,
  but income/expense allocations, loan terms, and household-service usage are
  documented synthetic assumptions, not observed data.
- Assumed monthly household-service rates (INR): {'cleaning': 1500, 'cooking': 4000, 'dishwashing': 800, 'laundry': 1000}

## Validation
- unique_user_ids: PASS
- income_positive: PASS
- expenses_nonneg: PASS
- dependents_le_family_size: PASS
- emi_nonneg: PASS
- assets_nonneg: PASS
- liabilities_nonneg: PASS
- investments_nonneg: PASS
- goal_amount_nonneg: PASS
- goal_year_after_reference: PASS
- valid_city_reference: PASS
- row_count_correct: PASS

Overall: ALL CHECKS PASSED

Output: `data/processed/user_financial_data.csv`, shape (10000, 30)
