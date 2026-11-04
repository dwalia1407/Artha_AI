# Database schema (migration 0001)

All timestamps are timezone-aware UTC. Transaction dates are calendar dates (Asia/Kolkata). Money is integer paise. UUID string primary keys.

| Table | Purpose | Key constraints |
|---|---|---|
| users | person; `auth_provider`, `auth_ref`, `email_verified_at` | unique email; unique (auth_provider, auth_ref) |
| local_credentials | password hash for the built-in provider | PK/FK user_id |
| households | name, owner_id | FK owner |
| household_memberships | role (owner/viewer), status (active/invited/removed) | unique (household_id, user_id); CHECKs on role/status |
| accounts | per household; type, institution, currency, status | unique (household_id, account_name); currency CHECK = INR |
| imports | one uploaded file: hash, filename, parser_version, status (staged/completed/failed), counts, error_message | partial unique index (account_id, file_hash) where status <> 'failed' |
| staged_transactions | parsed rows awaiting review, with raw_row JSON, validation_errors, potential_duplicate, edit_history | unique (import_id, source_row_number); CHECKs on statuses |
| transactions | approved ledger rows with provenance (import_id, source_row_number), correction_metadata | unique (import_id, source_row_number); CHECK amount >= 0, currency INR, direction, type list, approval_status = 'approved'; indexes on (household_id, transaction_date) and (account_id, date, amount, direction) |

Differences from the master prompt's field list: added `household_id`, `account_id`, `raw_row`, `description` (editable copy next to `original_description`), `category`, `matched_transaction_id`, `potential_duplicate`, `duplicate_candidates`, `edit_history`, `transaction_id` and `updated_at` on staged rows; `uploaded_by` and `error_message` on imports; `matched_transaction_id` on transactions. `StagedTransaction.suggested_category` exists but nothing fills it yet.

Commands: `alembic upgrade head`, `alembic downgrade base`, `alembic current`.
