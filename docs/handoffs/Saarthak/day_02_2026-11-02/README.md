# Day 2 — Shared ML preparation and evaluator

Prepared 2 November 2026 by Disha. Day labels identify planned milestones; they do not claim earlier delivery. Status: saved locally, not sent; recipient acceptance pending.

Start with [ML run instructions](../../../../ml/README.md). Files: `ml/contracts/v2/` for dataset/manifest/label map; `ml/shared/` for preparation, majority helper and evaluator; `ml/requirements.txt` for verified dependencies.

Approved allocation: train 375, validation 80, test 84. All 13 categories have at least three rows per split. Use the same template-family split and fitted TF-IDF for every model. TF-IDF uses words and word pairs, max_features=2000, lowercase, no stop-word removal, min_df=1, L2 normalization; defaults are documented in the ML guide. Actual fitted vocabulary: 950 features.

From the repository root:

```powershell
python -m unittest discover -s ml/tests -v
python -m ml.shared.prepare
```

Preparation has already run in this workspace; do not rerun into the existing output folder. In a fresh checkout, it generates `ml/artifacts/shared_v2/`. Artifacts are ignored by Git. Pair each sparse matrix with its ordered `*_rows.csv`; reuse the saved vectorizer without refitting. Hashes are recorded in `preparation.json` and contract `split_audit.json`.

Verified: nine tests passed and saved artifacts reloaded correctly. No classifiers, actual majority-baseline predictions or test scores have been produced. Test descriptions were not transformed. One joblib/NumPy deprecation warning occurred during a successful roundtrip test.

Evaluator inputs are category-name predictions keyed by transaction ID. Missing/extra/duplicate IDs and unknown labels fail. Macro-F1 is primary; the evaluator also reports accuracy, weighted-F1, per-class precision/recall/support, worst-class recall and confusion matrix. Operational helpers measure wall time, Python-traced peak allocations (not full process RAM) and artifact size.

Your assigned implementation is majority baseline and Logistic Regression. LR settings/tuning limits are not finalized here. Obtain the agreed settings before training. Compare on validation; do not evaluate test until model choices are frozen and final evaluation is authorized. Return commands, artifact hashes, measured results and limitations for Disha's acceptance.
