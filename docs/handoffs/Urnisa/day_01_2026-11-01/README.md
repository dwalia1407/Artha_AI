# Day 1 — Monthly-summary tool contract

Prepared 2 November 2026 by Disha. Day labels identify planned milestones; they do not claim earlier delivery. Status: saved locally, not sent; recipient acceptance pending.

Read [the approved contract](../../../contracts.md) and [the test-only fixture](monthly_summary_fixture.json).

Your adapter will call `get_monthly_summary(auth_context, household_id, month)` and return the authoritative service result without recomputing totals. Biswa supplies trusted context and permission enforcement. Do not invent an authentication mechanism.

The fixture expects INR 50,000 income, INR 12,500 expenses and INR 37,500 cash surplus, encoded in paise. Five approved records are counted even though the internal transfer is excluded from arithmetic. It explicitly assumes complete coverage for a fictional household.

Acceptance request: confirm the output fields meet the tool's needs and retain the example for isolated adapter tests. Live connection remains pending the real service. This fixture itself does not test permissions.
