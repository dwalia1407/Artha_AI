# Architecture (Day 1-3)

## Repository audit (as received, 2 November 2026 snapshot)

- Content: a Python data pipeline (`src/`, pandas/numpy/matplotlib/openpyxl), processed datasets (`data/`), reports and results, a legacy folder, ML contracts and shared evaluator (`ml/`), docs and handoffs.
- No web framework, database, authentication, API, frontend, migrations or deployment configuration existed.
- No `AGENTS.md` file anywhere in the repository.
- The snapshot I worked on had no `.git` directory, so Git status could not be inspected; I only added files and changed one: `docs/contracts.md` (appended a section, Disha's text untouched). Nothing under `src/`, `ml/`, `data/`, `results/`, `reports/` or `legacy/` was modified. `requirements.txt` is untouched; web dependencies are in `requirements-app.txt`.
- `00_Master_Execution_Plan.md` was not provided; I worked from the Biswa brief and the master prompt.
- Compatibility notes: `src/` uses flat imports (`from utils import ...`), so the web code lives in a separate top-level package `app/` and never imports `src/`. Raw HCES is not needed and not referenced at runtime.

## Decisions

| Area | Choice | Why |
|---|---|---|
| Shape | Modular monolith, one Flask app | smallest thing that works; no microservice need |
| Backend | Flask 3 + Flask-SQLAlchemy / SQLAlchemy 2 | Python matches the repo; Flask was already familiar |
| Frontend | Server-rendered Jinja pages, plain CSS and ~15 lines of JS | no build step; testable with the Flask test client; strict CSP with no inline script/style |
| Database | PostgreSQL (psycopg2); SQLite only for fast local tests | production requirement; all tests also run on PostgreSQL 16 |
| Migrations | Alembic, `migrations/versions/0001_initial_schema.py` | checked against the models by a test |
| Auth | Built-in "local" provider (scrypt password hashes, signed cookie session) behind `app/auth/service.py` | see limitation below |
| IDs | UUID strings generated in Python | portable across SQLite/PostgreSQL |
| Money | integer paise (`BigInteger`), parsed with `Decimal` text, never floats | brief requirement |

Limitation on auth: the brief asks for an established provider. No provider credentials exist in this environment, so I did not wire one. `users.auth_provider` and `users.auth_ref` are the boundary where Supabase/Firebase/etc. would attach; password hashes live in a separate table an external provider would not use.

## Layout

```
app/
  __init__.py        factory, CSRF, security headers, error handling, /healthz
  config.py          env-based config; production refuses unsafe settings
  models.py          all tables
  constants.py       currency, roles, statuses, types, categories
  errors.py          typed errors
  session.py         login/logout, trusted AuthContext
  auth/              register, login, email verification, profile, mailer
  households/        households, membership checks (authorization), accounts
  imports/           csv_parser (pure), service (upload/stage/duplicates), review (edit/approve)
  ledger/            list, correct, month feed for the finance service
  integrations/      finance gateway (Disha's service plugs in here)
  api/               JSON API under /api/v1
  web/               HTML pages
  templates/ static/
migrations/  tests/  docs/
```

## Authorization model

Every household-scoped function calls `require_member(actor_id, household_id, write=...)` with the actor id taken from the session. Resources fetched by their own id (account, import, staged row, transaction) are authorized through the household they belong to. Non-members get 404; viewers attempting writes get 403. Roles: `owner` (read/write) and `viewer` (read). Invitations and removal flows are Day 4; the `invited`/`removed` statuses exist in the schema and `removed` is already denied access.

## Import pipeline

upload -> size/type/encoding checks -> SHA-256 -> parse + validate every row -> stage (never the ledger) -> review (edit / reject / reopen / set type) -> approve (row lock, savepoint per row, ledger insert, unique `(import_id, source_row_number)` backstop). The raw file is not retained; the hash, row-level raw values and parser version are.
