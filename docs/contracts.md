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

---

# Biswa's application-side decisions (added 4 November 2026)

Status: implemented in `app/`, verified by the test suite, **not yet accepted by Disha or Urnisa**. Everything above this line is Disha's and was not changed.

## Ledger mapping for the monthly summary

| Contract concept | Where it lives |
|---|---|
| household | `households.id` (UUID string) |
| approved record | row in `transactions` (only approved rows can exist there; a CHECK enforces `approval_status = 'approved'`) |
| amount | `amount_minor`, non-negative integer paise; direction is separate (`credit` / `debit`) |
| currency | `currency`, always `INR` (CHECK) |
| date | `transaction_date`, a calendar date in Asia/Kolkata (no time part, so month boundaries need no conversion) |
| month | `YYYY-MM`; in-month means `first of month <= date < first of next month` |
| transaction type | `transaction_type`: income, purchase, fee, refund, internal_transfer, card_settlement, cash_withdrawal, investment, loan_payment |
| category | `category`, separate from type; the 13 labels in `ml/contracts/v2/label_map.json` |
| matched refund | `matched_transaction_id` (same household only) |

Rows with no type, an unclear type, validation errors, a pending state or a rejected state never reach `transactions`. "Unclear credit / unmatched refund / ambiguous transfer" therefore stay in staging; an *unmatched refund* can still be approved (matched id empty) and the finance service is expected to exclude it with a warning.

## Trusted context and membership

`app.auth.context.AuthContext(user_id, email_verified, source)` is a frozen dataclass created only by `app.session.require_context()` from the signed session. Gateway: `app.integrations.finance.get_monthly_summary(auth_context, household_id, month)`.

Order of checks: AuthContext instance (else `Unauthenticated`), `household_id` present and month format valid (else `InvalidRequest`), active membership (else `NotFound`, so ids cannot be probed), service registered (else `ServiceUnavailable`). The service result is returned unchanged. Plug the real service in with `finance.register_service(func)`.

Read-only feed for the service: `app.ledger.service.approved_records_for_month(auth_context, household_id, month)` returns dicts with `transaction_id, date, type, category, direction, amount_minor, currency, matched_transaction_id, approved`. It checks membership itself.

## Typed errors (`app/errors.py`)

| Class | code | HTTP |
|---|---|---|
| Unauthenticated | `unauthenticated` | 401 |
| Unauthorized (e.g. viewer write) | `unauthorized` | 403 |
| EmailNotVerified | `email_not_verified` | 403 |
| NotFound (also non-member) | `not_found` | 404 |
| MissingData | `missing_data` | 404 |
| Conflict | `conflict` | 409 |
| InvalidRequest | `invalid_request` | 400 |
| ServiceUnavailable | `service_unavailable` | 503 |

JSON form: `{"error": {"code", "message", "details"}}`. This is a proposal for Urnisa's adapter and Disha's service; it is not final until they accept it.

## Open decisions (need Disha)

1. Source of "explicitly confirmed complete coverage". The ledger has no coverage table yet; the test double takes it as an argument.
2. Coverage enum values beyond `complete` and warning/error codes.
3. Whether the type/direction sanity rules are acceptable: income and refund must be credits; purchase, fee, loan payment and cash withdrawal must be debits; other types may be either. These are my structural checks, not Disha's finance rules.
4. Whether the service reads the ledger via the feed function above or queries tables directly.
5. `predict_categories` return fields. Not integrated; `staged_transactions.suggested_category` exists and stays empty.
