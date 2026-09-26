# QA Report

- Total data-pipeline test cases executed: 20
- Passed: 20
- Failed: 0

All results above were produced by actually running each test row through the
real `feature_engineering.engineer()` function (imported, not reimplemented) and
checking the output. No PASS/FAIL result in this report was hand-written.

Several tests intentionally document that a given check belongs to a different
pipeline stage (validation.py's dataset-level checks, or user_generation.py's
generation-time checks) rather than feature_engineering.py; this reflects how the
pipeline is actually structured (row-level transforms vs dataset-level validation),
not a gap.

Full machine-readable results: `results/data_pipeline_qa.csv`
