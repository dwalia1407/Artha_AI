# Rubric Mapping

Team project, 15 marks total. Each section below points to the actual
generated evidence for that section.

## Section 1 - Problem Identification & Objectives (2 marks)
- Problem statement, motivation, objectives, intended application:
  `README.md` (Problem Statement & Objectives sections) and
  `context.md` (original project brief, section 1).

## Section 2 - Data Understanding (3 marks)
- Dataset inventory with measured row/column counts and missingness:
  `reports/data_inventory.md`
- Per-source processing logs (actual figures): `reports/cpi_processing_log.md`,
  `reports/rbi_processing_log.md`, `reports/city_processing_log.md`,
  `reports/hces_processing_log.md`, `reports/hces_processing.md`
- Target definition and its limitations: `reports/feature_engineering_log.md`,
  `reports/ml_methodology_plan.md` (Section 1)

## Section 3 - Data Preprocessing (3 marks)
- Cleaning, missing-value treatment, duplicate handling, structural vs
  accidental missingness distinctions: `reports/cpi_processing_log.md`,
  `reports/rbi_processing_log.md`, `reports/hces_processing_log.md`
- City matching / merge validation: `reports/city_processing_log.md`,
  `reports/integration_log.md`
- Synthetic user generation and its validation: `reports/user_generation_log.md`
- Outlier handling (flagged, not deleted): `reports/data_quality_report.md`,
  `results/tables/outlier_summary.csv`
- Feature engineering with domain justification: `reports/feature_engineering_log.md`,
  `src/feature_engineering.py`

## Section 4 - Exploratory Data Analysis (2 marks)
- 15 plots: `results/eda/01_*.png` through `15_*.png`
- Descriptive statistics: `results/tables/eda_descriptive_stats.csv`
- Narrative report with observations and limitations: `reports/eda_report.md`

## Section 5 - Data Splitting & Methodology Planning (2 marks)
- Train/validation/test proposal, leakage-prevention rules, proposed
  algorithms, evaluation metrics, validation methodology:
  `reports/ml_methodology_plan.md` (Sections 3-9)

## Section 6 - Project Scope & Future ML Plan (1.5 marks)
- Current scope vs future ML implementation, proposed models, future
  validation requirements, limitations, deployment roadmap:
  `reports/ml_methodology_plan.md` (Sections 10-11), `README.md`
  (Limitations & Future Work)

## Section 7 - Teamwork & Presentation (1.5 marks)
- Documentation set (this file plus every report listed above),
  reproducibility instructions: `README.md` (Reproducibility)
- Presentation-ready content: `presentation/presentation_content.md`
- Team contribution record: `reports/team_contributions.md`
  (placeholders where actual team-member detail was not provided -
  filled with real names/roles only if supplied)

## Individual Role (5 marks)
Role-specific evidence depends on the individual's assigned role; the
generated `src/*.py` modules are each self-contained and can be
attributed to a specific team member/role in `reports/team_contributions.md`.

## What was intentionally NOT done, and why
- No ML model was trained, no ML metric was computed, no ML prediction
  was made - by explicit instruction, this project stops at a fully
  specified future ML plan (Sections 5-6 of the rubric).
- HCES category-wise expenditure benchmarks (food/education/medical/etc.)
  were not built because the official item-classification codebook was
  not supplied with the raw data (`reports/hces_processing.md`, "What
  was NOT attempted").
- HCES benchmarks are not joined to individual synthetic users, because
  users do not carry a genuine state/sector field and guessing a
  city-to-state mapping would violate the project's no-guessing rule
  (`reports/integration_log.md`).
