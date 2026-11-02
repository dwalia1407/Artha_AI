# Shared category-classification preparation and evaluation

Uses the approved synthetic-only version-2 dataset: 375 training, 80 validation and 84 test descriptions, 13 categories. All models must use the same contract, text processor and feature columns. No classifiers have been trained by this package.

## Run from the Artha_AI repository root

```powershell
python -m unittest discover -s ml/tests -v
python -m ml.shared.prepare
```

Dependencies are pinned in `ml/requirements.txt` to the versions verified on Python 3.14.4. Existing installed packages were used; no packages were installed or upgraded. Preparation refuses to overwrite an existing `ml/artifacts/shared_v2` directory. Generated artifacts are ignored by Git and can be reproduced in a fresh checkout.

## Shared inputs and artifacts

`ml/contracts/v2` contains the dataset, label map, manifest and hashes. The loader checks fixed hashes, complete ID membership, category coverage and group/description overlap. `description` is the only feature input; IDs, labels and template groups are excluded. Use the integer encoding in `label_map.json` consistently when an estimator requires it; convert predictions back to category names for evaluation.

TF-IDF uses words and word pairs, at most 2,000 features, lowercase, no stop-word removal, min_df=1, max_df=1.0 and L2 normalization. Other options are scikit-learn 1.9.0 defaults. In particular, its default tokenizer drops single-character tokens and treats punctuation as separators; no stemming or additional scaler is used. These settings were approved before fitting.

Preparation fits on training rows only. It saves `tfidf.joblib`, sparse `train.npz` and `validation.npz`, and corresponding ordered `*_rows.csv` ID/category files. `preparation.json` records versions, timings, shapes and artifact hashes. Each matrix row corresponds to the same row in its companion CSV. Reuse these matrices and the saved vectorizer across all four classifiers; do not refit on validation/test. Only load the locally generated joblib artifact, not an arbitrary user-uploaded serialized file.

The actual preparation produced 950 features: training shape 375 x 950, validation shape 80 x 950. No test features or predictions were generated. Later final-test transformation must use the already fitted vectorizer after model selection is approved.

## Evaluation interface

```python
from ml.shared.evaluate import evaluate

# Supply exactly one category-name prediction per validation transaction ID.
report = evaluate(predictions)  # predictions: [{"transaction_id": "...", "category": "..."}, ...]
```

Predictions are joined by ID, not positional order. Missing, extra or duplicate IDs and unknown labels are rejected. Reports contain accuracy, macro-F1, weighted-F1, per-class precision/recall/F1/support, worst-class recall and a confusion matrix with explicit label order. Undefined precision is reported as zero and unpredicted labels are listed. Synthetic evidence is explicitly labelled.

Macro-F1 is the primary comparison metric; model selection still requires user review. The majority-category helper uses only supplied training labels and breaks ties by the fixed label map. It is available to Saarthak; no real baseline predictions or scores have been generated here.

Test scoring is blocked unless the caller explicitly sets `final_test_authorized=True`. This is an accidental-use guard, not an access-control or one-run enforcement mechanism. Use it only after user approval of frozen model settings/selection. Evaluate final candidates once; do not tune based on test results. Test source rows remain readable for contract checks.

## Operational measurements

Wrap future fit/predict operations with `measure_call(function, *args, **kwargs)` to record elapsed wall time and peak Python-traced memory. Timing includes the tracing overhead; use the same procedure and hardware for comparisons and record prediction batch size. This memory measure may exclude native-library allocations and is not total process RAM. `artifact_size(path)` measures one exported pipeline file in bytes. No model timing, memory or size results exist yet.

## Checks and remaining work

Nine unit tests passed: contract coverage, changed-holdout vocabulary/IDF isolation, vectorizer save/load, independently hand-calculated metrics with shuffled prediction order, invalid predictions, unpredicted classes, test gate, majority behavior, and measurement cleanup. The roundtrip check emits a joblib/NumPy deprecation warning under these installed versions but passes.

The small synthetic holdouts cannot establish real-statement accuracy. Remaining cleaned-description repetitions stay inside their original split. Merchant overlap is intentional; this is a template-family evaluation. No classifier settings, tuning limits or deployment decision are implied by this implementation. Finance contracts and summary fixtures remain separate pending work.
