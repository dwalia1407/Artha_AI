# Approved shared ML dataset and split — version 2

Approved on 2 November 2026 for Artha AI's shared synthetic spending-category experiments. Use this version instead of version 1. This packet was copied into the repository for the shared implementation; version 1 and downloaded originals remain preserved in the workspace research folder.

| Split | Rows | Share | Minimum examples per category |
|---|---:|---:|---:|
| Training | 375 | 69.57% | 13 |
| Validation | 80 | 14.84% | 3 |
| Test | 84 | 15.58% | 3 |

All 13 categories occur in each split. `dataset.csv` contains transaction_id, description, category and group_id. Join `split_manifest.csv` on transaction_id; do not create a separate split for each model. `label_map.json` supplies the common alphabetical label encoding. `split_audit.json` records counts, policy and SHA-256 hashes. Dataset and label-map bytes are identical to version 1; only split assignments changed.

## Grouping and selection

Ten broad template families stay intact. Training: POS, merchant/city, dash-form UPI, natural language, NEFT, slash-form UPI. Validation: IMPS and bare merchant. Test: merchant/reference and ACH. All natural-language phrases stay together. Identical cleaned descriptions cannot cross splits. Merchant names may occur across splits, so this is a template-family holdout, not an unseen-merchant evaluation.

The revised allocation was selected by exhaustively examining assignments of these ten families to three splits. Each category must have at least three rows per split. Among feasible assignments, minimize the sum of absolute deviations from 70/15/15 row proportions; shuffle the sorted family names with Python random seed 42 for deterministic tie-breaking. No model predictions, model scores or learned text statistics were used. The user approved this concrete allocation before it was saved.

The workspace research script `work/disha_dataset_research/save_split_v2.py` reproduces the approved assignment from the hash-verified version-1 dataset and label map. It validates constraints and refuses to overwrite an existing version-2 folder. Repository users should consume the included manifest rather than rerunning the split search.

## Experiment rules and limits

All four planned model candidates must use this dataset, label map and split manifest. Fit TF-IDF and all other learned preprocessing on training rows only. Tune and choose models using validation only. Evaluate final frozen candidates on test once; no test-based tuning. Shared TF-IDF preparation and evaluation have since been approved and implemented; see `ml/README.md`.

This is synthetic-only proof-of-mechanism evidence. Some holdout categories contain only three examples, so per-category scores will be unstable. The 539 rows contain 525 distinct cleaned descriptions; remaining repeats stay within one split. Category labels do not establish financial transaction type, direction, account ownership or approval. No financial totals should be calculated from these records.

No models have been trained, and no model performance has been measured. This packet does not complete the finance-service or evaluator portions of Disha's November 1–2 tasks.
