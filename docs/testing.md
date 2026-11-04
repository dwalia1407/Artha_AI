# Testing

```
pytest -q                                   # SQLite, ~16 s
TEST_DATABASE_URL=postgresql://USER:PASS@localhost:5432/artha_test pytest -q   # PostgreSQL (drops/recreates tables and the public schema of that database)
```

Files: `test_auth` (registration, login/logout, invalid credentials, protected routes, profile persistence, verification valid/expired/tampered/forged, verification enforcement, delivery failure, CSRF, headers), `test_authorization` (household/account/import/staged/transaction/summary isolation by changing ids, viewer read-only, removed member, web pages, HTML escaping), `test_csv_parser`, `test_import_flow` (upload rejections, staging, edit/reject/reopen/approve, provenance, duplicate approval, exact re-import, overlapping statements, legitimate repeats), `test_finance_semantics` (contract fixture through the real import/approve flow, no-data, transfers, card settlement, cash, investment, loan, refunds, month boundaries, gateway checks), `test_persistence_and_schema` (restart persistence, migrations match models, label map, INR formatting), `test_concurrency_pg` (PostgreSQL only).

`tests/doubles/reference_summary.py` is a **test double** written from the contract table. It is not Disha's service, so the semantic tests show the ledger feeds the contract correctly, not that Disha's arithmetic is correct.

Not covered: browser/JS behaviour and accessibility audits (pages were only rendered through the Flask test client), real SMTP delivery, login rate limiting, load.
