# Biswa handoff log: Days 1-3 (independent work)

Written 4 November 2026. Scope: Day 1 foundation, Day 2 auth/households/accounts, Day 3 CSV import and ledger. Days 4-10 are not started.

## Status summary

| Area | Status |
|---|---|
| Repo audit, architecture, schema, contracts, env example, migrations | Done |
| App shell, `/healthz`, config, error handling | Done |
| Registration, login, logout, sessions, profile editing | Done (built-in provider) |
| Email verification | Token flow done and tested; **real delivery untested** (no SMTP) |
| Established auth provider (Supabase/Firebase/etc.) | **Not done**: no credentials; boundary documented |
| Households, memberships, owner/viewer authorization, accounts | Done |
| CSV upload, parse, validate, stage, review, approve/reject, ledger | Done |
| Exact re-import protection, possible-duplicate flagging | Done |
| Frontend pages (10 requested) | Done as server-rendered pages; not checked in a real browser |
| Persistence across restart/logout/login | Verified on PostgreSQL with a real gunicorn kill and cold start |
| Deployment to a public URL | **Blocked**: needs hosting/DB/SMTP credentials |
| Finance service (Disha) | Not connected; gateway returns 503 until registered |
| Tool adapter (Urnisa), classifier, PDF, invitations, agent | Not in scope / not started |

## Evidence (actually run)

- `pytest -q` on SQLite: 84 passed, 1 skipped (the PostgreSQL-only concurrency test).
- `pytest -q` on PostgreSQL 16.15: 85 passed (includes simultaneous double-approval producing one ledger row, repeated 3 times, and a test that Alembic output matches the models).
- `alembic upgrade head` / `downgrade base` / `upgrade head` round trip on PostgreSQL succeeded.
- Existing `ml/tests`: 9 passed, unchanged.
- End-to-end over HTTP (gunicorn, 2 workers, PostgreSQL, `APP_ENV=production`): health 200; register without CSRF token rejected with 400; register, create household and account, upload CSV, approve 2 rows; exact re-upload returned `already_imported=true` and the ledger stayed at 2; logout gave 401; server process killed and confirmed down; cold restart; `/me` 401 before login; login 200; household and both ledger rows (Salary 5000000, Groceries 300000 paise) returned. Server logs contained none of the descriptions, amounts or the password.
- Disha's fixture (income 5,000,000 / expense 1,250,000 / surplus 3,750,000 paise, 5 records, complete, no warnings, v1) was pushed through the real upload, review and approval flow (including a refund matched to the grocery purchase) and compared with the **test double** output: equal. This proves the ledger can express the contract, not that Disha's service is right.

## Bugs found by tests and fixed during this work

1. `parse_amount` removed all spaces, so "10 20" became 1,020.00. Now rejected.
2. Type/direction sanity ("income" with a debit) was checked only on edits; a CSV could stage and approve it. Now validated at parse, edit and approval.
3. `LocalCredential` insert could precede the `User` insert; PostgreSQL's foreign key caught it (SQLite did not). Fixed with a flush.
4. A database URL passed as `postgresql://` selected the wrong driver. Normalised in `create_app`.
5. API clients had no way to get a CSRF token before first login. Added `GET /api/v1/csrf`.

## Known limitations

- No login rate limiting, no password reset or recovery (Day 4), no phone verification.
- Raw uploaded files are not stored; only hash, per-row raw values and parser version are kept. Private storage is not set up.
- Type is never guessed; CSVs without a `type` column need types set by hand (bulk "set type" exists).
- Duplicate re-check after an edit compares against the ledger only, not other pending imports.
- Ledger corrections cover category, type, matched id and description; amount/date/direction require re-import.
- The type/direction rules are mine and need Disha's confirmation.
- Web form offers two column layouts; custom header mapping is available via the service/API only.
- Month totals are not computed anywhere in this app; the summary page shows the finance service result or says it is not connected.
- Test accounts, `artha_dev`/`artha_test` databases and the dev password exist only in this sandbox.

## Outstanding external dependencies

- Disha: coverage-confirmation source and enum, warning/error codes, acceptance of ledger mapping and error format, `predict_categories` fields (see `docs/contracts.md`, "Open decisions").
- Urnisa: adapter should call `finance.get_monthly_summary` with an `AuthContext` supplied by the dispatcher; typed errors are in `app/errors.py`. Not integrated, nothing from Urnisa was received.
- You: hosting + managed PostgreSQL, SMTP or an auth provider, decision on the provider.

## Acceptance checklist

Day 1: audit done; architecture documented; shell runs; PostgreSQL + migrations work; contracts recorded; `.env.example` created. **Done.**
Day 2: auth and profile work (local provider); households and authorization enforced and tested; persistence verified; deployment **blocked** on credentials; external provider and real email delivery **not done**.
Day 3: upload, parse, staging, validation, editing, rejection, approval, ledger, exact re-import protection, duplicate detection, provenance, automated and security tests: **done and run**. Browser-level UI verification: **not done**.

Next receiver: Disha (finance service against `approved_records_for_month`), then Urnisa (adapter against the gateway).
