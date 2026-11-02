# Disha's approved finance and ML handoff contracts

Prepared 2 November 2026. Day 1 refers to the planned 1 November milestone, not a claim that these files were delivered that day. User-approved finance rules are recorded below; Biswa's integration acceptance is still pending. No finance service or authentication integration has been implemented here.

## Monthly summary

Logical interface: `get_monthly_summary(auth_context, household_id, month)`.

`auth_context` must come from Biswa's trusted backend. The service boundary must verify membership before returning household data. Do not accept an assistant-supplied identity as authentication. Concrete auth representation, application technology, storage schema and error format await Biswa; this document does not select them.

Use approved records only, INR only, and integer paise. Month is YYYY-MM with Asia/Kolkata boundaries. The application must preserve transaction type separately from spending category. Synthetic category predictions do not establish transaction approval, income, transfers or account ownership.

| Record | Approved treatment |
|---|---|
| Confirmed income | Add to income |
| Approved purchase or fee | Add to expenses |
| Matched purchase refund | Subtract from expenses in the month received; do not revise the original purchase month |
| Confirmed internal transfer | Exclude from income and expenses |
| Credit-card settlement | Exclude when the underlying purchases are recorded; flag incomplete coverage otherwise |
| Cash withdrawal or investment movement | Keep separate from spending totals |
| Loan payment | Keep separate from income and expense totals; warn that debt payments are excluded |
| Unclear credit, unmatched refund, ambiguous transfer | Exclude from totals pending review and surface a warning |

Cash surplus = included income minus included expenses. This is not bank-balance change or money available to spend, particularly because debt payments and other movements are excluded. Do not count a planned commitment as an actual payment.

No approved records means unknown totals (`null`), not fabricated zeroes. Partial coverage means recorded totals with an explicit warning. Complete coverage requires explicit confirmation; merely having some transactions is insufficient. The concrete source of coverage confirmation remains to be agreed with Biswa.

Summary keys: `household_id`, `month`, `currency`, `income_minor`, `expense_minor`, `cash_surplus_minor`, `transaction_count`, `coverage_status`, `warnings`, `calculation_version`. `transaction_count` counts all approved in-month records, including confirmed transfers excluded from totals. Exact coverage enum values beyond the approved example and warning/error codes remain pending; do not invent a production contract for them.

## Approved test-only example

For a hypothetical household with explicitly confirmed complete November coverage: salary INR 50,000; groceries INR 3,000; rent INR 10,000; matched grocery refund INR 500; confirmed internal transfer INR 5,000. Expected income = 5,000,000 paise; expense = 1,250,000 paise; cash surplus = 3,750,000 paise; transaction_count = 5; coverage_status = complete; warnings = []; calculation_version = v1.

Biswa and Urnisa each have the same JSON fixture in their Day 1 folder. It is illustrative input/output, not a database schema, proof of authorization, live household record or passing integration test. Urnisa's adapter must use the service result without recomputing arithmetic.

## ML contract

Use `ml/contracts/v2/dataset.csv`, `split_manifest.csv` and `label_map.json`. There are 539 synthetic category candidates, 13 labels, with 375 training / 80 validation / 84 test rows. Template families and identical cleaned descriptions stay within one split; merchants may repeat. Each category has at least three examples per split. Small synthetic holdouts do not establish real-statement performance.

Shared TF-IDF and evaluator: `ml/shared/`, usage in `ml/README.md`. Description is the only feature input. Train-only word/word-pair TF-IDF, maximum 2,000 features, actually produced 950 features. All models must reuse the same fitted representation and fixed manifest. Validation is for tuning and proposed selection; final test requires explicit approval after model choices are frozen. No classifiers or real baseline predictions have been produced.

Saarthak owns baseline/LR; Disha owns shared protocol and the other planned models. Classifier settings, tuning limits, deployment choice and finance implementation remain separate pending decisions.
