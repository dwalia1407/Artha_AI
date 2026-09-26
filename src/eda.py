"""
Exploratory Data Analysis on the final integrated dataset plus the
standalone CPI/RBI monthly context tables.

Saves plots to results/eda/ using plt.savefig() (non-interactive).
Descriptive stats go to results/tables/ and reports/eda_report.md.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from utils import PROCESSED_DIR, EDA_DIR, TABLES_DIR, REPORTS_DIR, write_log

FINAL_PATH = PROCESSED_DIR / "final_user_dataset.csv"


def savefig(name):
    path = EDA_DIR / name
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close()
    return path


def process():
    df = pd.read_csv(FINAL_PATH, parse_dates=["reference_month", "cpi_month", "rbi_month"])
    cpi = pd.read_csv(PROCESSED_DIR / "cpi_monthly_clean.csv", parse_dates=["month"])
    rbi = pd.read_csv(PROCESSED_DIR / "rbi_monthly_clean.csv", parse_dates=["month"])

    plots_made = []

    # 1. Income distribution
    plt.figure(figsize=(6, 4))
    plt.hist(df["monthly_income"], bins=50, color="#3b6ea5")
    plt.title("Monthly Income Distribution (Synthetic Users)")
    plt.xlabel("Monthly income (INR)"); plt.ylabel("Count")
    plots_made.append(savefig("01_income_distribution.png"))

    # 2. Monthly expense distribution
    plt.figure(figsize=(6, 4))
    plt.hist(df["monthly_expenses"], bins=50, color="#a53b3b")
    plt.title("Monthly Expense Distribution (Synthetic Users)")
    plt.xlabel("Monthly expenses (INR)"); plt.ylabel("Count")
    plots_made.append(savefig("02_expense_distribution.png"))

    # 3. Monthly savings distribution
    plt.figure(figsize=(6, 4))
    plt.hist(df["monthly_savings"], bins=50, color="#3ba55d")
    plt.title("Monthly Savings Distribution (Synthetic Users)")
    plt.xlabel("Monthly savings (INR)"); plt.ylabel("Count")
    plots_made.append(savefig("03_savings_distribution.png"))

    # 4. Savings rate distribution
    plt.figure(figsize=(6, 4))
    plt.hist(df["savings_rate"].clip(-1, 1), bins=50, color="#3ba58f")
    plt.title("Savings Rate Distribution (clipped to [-1, 1])")
    plt.xlabel("Savings rate"); plt.ylabel("Count")
    plots_made.append(savefig("04_savings_rate_distribution.png"))

    # 5. EMI distribution (loan holders only)
    plt.figure(figsize=(6, 4))
    plt.hist(df.loc[df["has_loan"] == True, "emi_amount"], bins=50, color="#8a3ba5")
    plt.title("EMI Amount Distribution (Loan Holders Only)")
    plt.xlabel("EMI (INR)"); plt.ylabel("Count")
    plots_made.append(savefig("05_emi_distribution.png"))

    # 6. Net worth distribution
    plt.figure(figsize=(6, 4))
    plt.hist(df["net_worth"], bins=50, color="#a5883b")
    plt.title("Net Worth Distribution (Synthetic Users)")
    plt.xlabel("Net worth (INR)"); plt.ylabel("Count")
    plots_made.append(savefig("06_networth_distribution.png"))

    # 7. Income vs expenses
    plt.figure(figsize=(6, 5))
    plt.scatter(df["monthly_income"], df["monthly_expenses"], s=4, alpha=0.3, color="#3b6ea5")
    plt.title("Income vs Expenses")
    plt.xlabel("Monthly income (INR)"); plt.ylabel("Monthly expenses (INR)")
    plots_made.append(savefig("07_income_vs_expenses.png"))
    corr_income_exp = df["monthly_income"].corr(df["monthly_expenses"])

    # 8. Income vs savings
    plt.figure(figsize=(6, 5))
    plt.scatter(df["monthly_income"], df["monthly_savings"], s=4, alpha=0.3, color="#3ba55d")
    plt.title("Income vs Savings")
    plt.xlabel("Monthly income (INR)"); plt.ylabel("Monthly savings (INR)")
    plots_made.append(savefig("08_income_vs_savings.png"))
    corr_income_savings = df["monthly_income"].corr(df["monthly_savings"])

    # 9. EMI ratio vs savings rate
    plt.figure(figsize=(6, 5))
    plt.scatter(df["emi_ratio"], df["savings_rate"].clip(-1, 1), s=4, alpha=0.3, color="#a53b3b")
    plt.title("EMI Ratio vs Savings Rate")
    plt.xlabel("EMI ratio"); plt.ylabel("Savings rate (clipped)")
    plots_made.append(savefig("09_emiratio_vs_savingsrate.png"))
    corr_emi_savings = df["emi_ratio"].corr(df["savings_rate"])

    # 10. Dependents vs expenses
    plt.figure(figsize=(6, 4))
    df.boxplot(column="monthly_expenses", by="dependents")
    plt.title("Monthly Expenses by Number of Dependents"); plt.suptitle("")
    plt.xlabel("Dependents"); plt.ylabel("Monthly expenses (INR)")
    plots_made.append(savefig("10_dependents_vs_expenses.png"))

    # 11. CPI inflation over time
    plt.figure(figsize=(7, 4))
    plt.plot(cpi["month"], cpi["combined_inflation"], color="#3b6ea5")
    plt.title("CPI Combined Inflation (General Index) Over Time")
    plt.xlabel("Month"); plt.ylabel("YoY inflation (%)")
    plots_made.append(savefig("11_cpi_inflation_over_time.png"))

    # 12. RBI repo rate over time
    plt.figure(figsize=(7, 4))
    plt.plot(rbi["month"], rbi["repo_rate"], color="#a53b3b")
    plt.title("RBI Repo Rate Over Time (Monthly, State-Propagated)")
    plt.xlabel("Month"); plt.ylabel("Repo rate (%)")
    plots_made.append(savefig("12_rbi_repo_rate_over_time.png"))

    # 13. Goal feasibility class distribution
    plt.figure(figsize=(5, 4))
    df["goal_feasibility"].value_counts().sort_index().plot(kind="bar", color=["#a53b3b", "#3ba55d"])
    plt.title("Rule-Derived Goal Feasibility Class Distribution")
    plt.xlabel("goal_feasibility (0=not feasible, 1=feasible)"); plt.ylabel("Count")
    plots_made.append(savefig("13_goal_feasibility_distribution.png"))

    # 14. City-level cost of living comparison (top 15 cheapest vs costliest, by sampled frequency)
    city_avg = df.groupby("city")["city_cost_one_person_inr"].mean().sort_values()
    top_bottom = pd.concat([city_avg.head(8), city_avg.tail(8)])
    plt.figure(figsize=(7, 6))
    top_bottom.plot(kind="barh", color="#3b6ea5")
    plt.title("City Cost of Living: 8 Lowest vs 8 Highest (Sampled Cities)")
    plt.xlabel("cost_one_person (INR)")
    plots_made.append(savefig("14_city_cost_comparison.png"))

    # 15. HCES expenditure benchmark comparison (state x sector, avg total_consumption_pc)
    bench = pd.read_csv(PROCESSED_DIR / "hces_benchmarks.csv")
    sector_avg = bench.groupby("Sector")["total_consumption_pc"].mean()
    plt.figure(figsize=(5, 4))
    sector_avg.plot(kind="bar", color=["#3ba58f", "#8a3ba5"])
    plt.title("HCES: Avg Per-Capita Consumption by Sector (1=Rural, 2=Urban)")
    plt.xlabel("Sector code"); plt.ylabel("Avg total_consumption_pc (INR/month)")
    plots_made.append(savefig("15_hces_sector_comparison.png"))

    # Descriptive statistics table
    numeric_cols = ["age", "monthly_income", "monthly_expenses", "monthly_savings",
                     "savings_rate", "emi_ratio", "rent_burden", "net_worth",
                     "assets", "liabilities", "investments", "goal_amount",
                     "goal_horizon_years", "future_goal_cost"]
    desc = df[numeric_cols].describe().T
    desc.to_csv(TABLES_DIR / "eda_descriptive_stats.csv")

    categorical_cols = ["financial_goal", "risk_tolerance", "has_loan", "owns_home"]
    cat_summary_lines = []
    for c in categorical_cols:
        vc = df[c].value_counts()
        pct = (vc / len(df) * 100).round(2)
        cat_summary_lines.append(f"### {c}")
        for k, v in vc.items():
            cat_summary_lines.append(f"- {k}: {v} ({pct[k]}%)")
        cat_summary_lines.append("")

    report = [
        "# EDA Report",
        "",
        "## 1. Purpose",
        "Exploratory analysis of the final synthetic user financial dataset (10,000 rows)",
        "and the CPI/RBI monthly economic context tables, to surface distributions,",
        "relationships, and data-quality signal ahead of any future modelling.",
        "",
        "## 2. Dataset overview",
        f"- Final dataset shape: {df.shape}",
        f"- CPI monthly rows: {cpi.shape[0]} ({cpi['month'].min().date()} -> {cpi['month'].max().date()})",
        f"- RBI monthly rows: {rbi.shape[0]} ({rbi['month'].min().date()} -> {rbi['month'].max().date()})",
        "",
        "## 3. Univariate analysis",
        "See plots 01-06 (income, expenses, savings, savings rate, EMI, net worth) in results/eda/.",
        "",
        desc.round(2).to_string(),
        "",
        "### Categorical variables",
    ] + cat_summary_lines + [
        "## 4. Bivariate analysis",
        f"- Income vs expenses correlation: {corr_income_exp:.3f} (plot 07)",
        f"- Income vs savings correlation: {corr_income_savings:.3f} (plot 08)",
        f"- EMI ratio vs savings rate correlation: {corr_emi_savings:.3f} (plot 09)",
        "- Monthly expenses by dependents: see boxplot (plot 10).",
        "",
        "Observation: income and expenses show a positive association in the synthetic",
        "dataset (this is a designed property of the generator, which allocates expense",
        "buckets as fractions of income, not an inferred real-world causal relationship).",
        "",
        "## 5. Economic trends",
        "- CPI combined inflation over time: plot 11. The 2013 series start has no",
        "  inflation value (structural missingness, documented in cpi_processing_log.md).",
        "- RBI repo rate over time: plot 12, monthly state-propagated series.",
        "",
        "## 6. Financial relationships",
        f"- EMI ratio vs savings rate correlation is {corr_emi_savings:.3f}. This is an association in the synthetic generator, not a causal estimate.",
        "  Because EMI amount and post-EMI monthly savings are constructed from the same synthetic income profile, the relationship is generator-induced rather than evidence about real household behaviour.",
        "",
        "## 7. Target distribution",
        f"- goal_feasibility class counts: {df['goal_feasibility'].value_counts().to_dict()} (plot 13)",
        "- This is the RULE-DERIVED target described in feature_engineering_log.md, not an",
        "  observed real-world outcome.",
        "",
        "## 8. Outlier findings",
        "See reports/data_quality_report.md and results/tables/outlier_summary.csv for the",
        "full IQR-based outlier flagging (income, expenses, savings, EMI, assets,",
        "liabilities, investments, goal amount). No values were deleted; the synthetic",
        "generator does not produce extreme values beyond what its own distributions allow,",
        "so flagged points reflect the tails of those distributions rather than corrupted data.",
        "",
        "## 9. Key observations",
        "- The dataset is fully synthetic; distributional shapes reflect the generator's",
        "  documented assumptions (city-scaled income, fraction-of-income expense buckets),",
        "  not measured population behaviour.",
        "- CPI and RBI monthly context are real, cleaned government data series and are",
        "  correctly attached to each user's reference month with zero unmatched rows.",
        "- HCES benchmarks are computed from real survey data but are not yet joined to",
        "  individual users (see integration_log.md for why).",
        "",
        "## 10. Limitations",
        "- Associations described above are associations in synthetic, generator-designed",
        "  data, not causal claims about real financial behaviour.",
        "- City-level cost comparison (plot 14) reflects the LivingCost dataset's own",
        "  point estimates, not a verified independent source.",
    ]
    write_log(REPORTS_DIR / "eda_report.md", report)
    print(f"[EDA] {len(plots_made)} plots written to results/eda/")
    return df


if __name__ == "__main__":
    process()
