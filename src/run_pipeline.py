"""
Single entry point for the Artha AI data pipeline.

Run from the project root:
    python3 src/run_pipeline.py

Executes, in order: data inventory, CPI, RBI, city, HCES, synthetic
users, integration, feature engineering, validation, EDA, QA, hidden QA.

Does NOT train any ML model - that is out of scope for this submission
(see reports/ml_methodology_plan.md).
"""

import sys
import time

STAGES = [
    ("Data inventory", "data_inspection", "process"),
    ("CPI processing", "cpi_processing", "clean"),
    ("RBI processing", "rbi_processing", "clean"),
    ("City processing", "city_processing", "process"),
    ("HCES processing", "hces_processing", "process"),
    ("Synthetic user generation", "user_generation", "process"),
    ("Integration", "integration", "process"),
    ("Feature engineering", "feature_engineering", "process"),
    ("Validation", "validation", "process"),
    ("EDA", "eda", "process"),
    ("Pipeline QA (test cases)", "qa_tests", "process"),
    ("Hidden QA", "generate_hidden_qa", "process"),
]


def main():
    for label, module_name, func_name in STAGES:
        print(f"\n=== {label} ({module_name}.py) ===")
        t0 = time.time()
        module = __import__(module_name)
        getattr(module, func_name)()
        print(f"--- done in {time.time() - t0:.1f}s ---")
    print("\nPipeline complete. See reports/ and results/ for all outputs.")
    print("No ML model was trained. See reports/ml_methodology_plan.md for the future plan.")


if __name__ == "__main__":
    sys.exit(main())
