# Hidden QA

- Hidden input rows: 4
- Columns checked against independently computed expected values: ['disposable_income', 'monthly_savings', 'savings_rate', 'emi_ratio', 'rent_burden', 'net_worth', 'goal_horizon_years', 'future_goal_cost', 'goal_feasibility']
- Mismatched columns: none
- Overall: ALL MATCH

Expected values were computed with formulas written independently in
feature_engineering.py (see generate_hidden_qa.py `compute_expected`), not by calling
the pipeline function on itself, so this is a genuine cross-check rather than a
tautological pass.
