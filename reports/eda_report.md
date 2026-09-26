# EDA Report

## 1. Purpose
Exploratory analysis of the final synthetic user financial dataset (10,000 rows)
and the CPI/RBI monthly economic context tables, to surface distributions,
relationships, and data-quality signal ahead of any future modelling.

## 2. Dataset overview
- Final dataset shape: (10000, 73)
- CPI monthly rows: 156 (2013-01-01 -> 2025-12-01)
- RBI monthly rows: 156 (2013-01-01 -> 2025-12-01)

## 3. Univariate analysis
See plots 01-06 (income, expenses, savings, savings rate, EMI, net worth) in results/eda/.

                      count        mean         std         min         25%         50%         75%          max
age                 10000.0       42.84       12.35       22.00       32.00       43.00       54.00        64.00
monthly_income      10000.0    35232.51    19828.31     8000.00    21358.50    30729.00    44039.25    208625.00
monthly_expenses    10000.0    22818.50    11704.69     2190.00    14823.00    21543.00    28610.50    117369.00
monthly_savings     10000.0     9610.89    13595.89   -51578.00      719.25     8460.50    16570.75    101812.00
savings_rate        10000.0        0.19        0.42       -5.43        0.03        0.27        0.48         0.79
emi_ratio           10000.0        0.08        0.11        0.00        0.00        0.00        0.16         0.35
rent_burden         10000.0        0.31        0.40        0.00        0.00        0.24        0.46         6.06
net_worth           10000.0   909713.18   944973.19 -4531215.00   309721.00   722977.50  1325720.00  11443123.00
assets              10000.0  1109271.30   922606.12    31151.00   448202.00   873031.00  1489975.00  11443123.00
liabilities         10000.0   199558.12   425110.72        0.00        0.00        0.00   224693.00   5569200.00
investments         10000.0   351849.13   302692.10        4.00   132265.50   275365.50   482225.00   2797199.00
goal_amount         10000.0  3745869.67  3009186.35   100532.00  1583399.75  2980509.00  5007615.25  27937955.00
goal_horizon_years  10000.0       10.07        5.51        1.00        5.00       10.00       15.00        19.00
future_goal_cost    10000.0  6341225.77  5477576.53   110836.53  2523382.97  4806343.27  8442248.75  50172553.22

### Categorical variables
### financial_goal
- wedding: 1507 (15.07%)
- retirement: 1479 (14.79%)
- vehicle_purchase: 1458 (14.58%)
- emergency_fund: 1443 (14.43%)
- travel: 1409 (14.09%)
- child_education: 1394 (13.94%)
- home_purchase: 1310 (13.1%)

### risk_tolerance
- medium: 3378 (33.78%)
- high: 3313 (33.13%)
- low: 3309 (33.09%)

### has_loan
- False: 6001 (60.01%)
- True: 3999 (39.99%)

### owns_home
- False: 6516 (65.16%)
- True: 3484 (34.84%)

## 4. Bivariate analysis
- Income vs expenses correlation: 0.714 (plot 07)
- Income vs savings correlation: 0.728 (plot 08)
- EMI ratio vs savings rate correlation: -0.267 (plot 09)
- Monthly expenses by dependents: see boxplot (plot 10).

Observation: income and expenses show a positive association in the synthetic
dataset (this is a designed property of the generator, which allocates expense
buckets as fractions of income, not an inferred real-world causal relationship).

## 5. Economic trends
- CPI combined inflation over time: plot 11. The 2013 series start has no
  inflation value (structural missingness, documented in cpi_processing_log.md).
- RBI repo rate over time: plot 12, monthly state-propagated series.

## 6. Financial relationships
- EMI ratio vs savings rate correlation is -0.267. This is an association in the synthetic generator, not a causal estimate.
  Because EMI amount and post-EMI monthly savings are constructed from the same synthetic income profile, the relationship is generator-induced rather than evidence about real household behaviour.

## 7. Target distribution
- goal_feasibility class counts: {0: 9302, 1: 698} (plot 13)
- This is the RULE-DERIVED target described in feature_engineering_log.md, not an
  observed real-world outcome.

## 8. Outlier findings
See reports/data_quality_report.md and results/tables/outlier_summary.csv for the
full IQR-based outlier flagging (income, expenses, savings, EMI, assets,
liabilities, investments, goal amount). No values were deleted; the synthetic
generator does not produce extreme values beyond what its own distributions allow,
so flagged points reflect the tails of those distributions rather than corrupted data.

## 9. Key observations
- The dataset is fully synthetic; distributional shapes reflect the generator's
  documented assumptions (city-scaled income, fraction-of-income expense buckets),
  not measured population behaviour.
- CPI and RBI monthly context are real, cleaned government data series and are
  correctly attached to each user's reference month with zero unmatched rows.
- HCES benchmarks are computed from real survey data but are not yet joined to
  individual users (see integration_log.md for why).

## 10. Limitations
- Associations described above are associations in synthetic, generator-designed
  data, not causal claims about real financial behaviour.
- City-level cost comparison (plot 14) reflects the LivingCost dataset's own
  point estimates, not a verified independent source.
