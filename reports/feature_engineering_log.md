# Feature Engineering Log

- Input rows: 10000, columns: 62
- Output rows: 10000, columns: 73
- ANNUAL_INFLATION_ASSUMPTION = 0.05 (explicit planning assumption, NOT observed CPI inflation, NOT used to fill any missing value)

## Rule-derived goal_feasibility target
- Class counts: {0: 9302, 1: 698}
- Feasible rate: 0.070
- monthly_savings is defined as post-expense, post-EMI cash surplus; investments
  are added separately to projected_savings.
- This target is DETERMINISTICALLY derived from monthly_savings, investments,
  goal_amount and goal_horizon_years in this same row. It demonstrates how a
  future ML target would be structured; it is NOT a real-world observed outcome,
  and high accuracy from any future model trained on it would mainly show the
  model can reproduce the rule, not that it predicts real financial outcomes.

## Feature summary (describe)
       disposable_income  monthly_savings  savings_rate  emi_ratio  rent_burden    net_worth  goal_horizon_years  future_goal_cost
count           10000.00         10000.00      10000.00   10000.00     10000.00     10000.00            10000.00          10000.00
mean             9610.89          9610.89          0.19       0.08         0.31    909713.18               10.07        6341225.77
std             13595.89         13595.89          0.42       0.11         0.40    944973.19                5.51        5477576.53
min            -51578.00        -51578.00         -5.43       0.00         0.00  -4531215.00                1.00         110836.53
25%               719.25           719.25          0.03       0.00         0.00    309721.00                5.00        2523382.97
50%              8460.50          8460.50          0.27       0.00         0.24    722977.50               10.00        4806343.27
75%             16570.75         16570.75          0.48       0.16         0.46   1325720.00               15.00        8442248.75
max            101812.00        101812.00          0.79       0.35         6.06  11443123.00               19.00       50172553.22
