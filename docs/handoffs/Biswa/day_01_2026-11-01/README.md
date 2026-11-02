# Day 1 — Finance contract and summary fixture

Prepared 2 November 2026 by Disha. Day labels identify planned milestones; they do not claim earlier delivery. Status: saved locally, not sent; recipient acceptance pending.

Read [the approved contract](../../../contracts.md) and [the test-only fixture](monthly_summary_fixture.json).

Delivered here: logical monthly-summary interface, approved refund/transfer/debt treatment, integer-paise output fields, coverage behavior, and the hand-calculated example. Refunds reduce expenses in their receipt month. Loan payments stay separate with an exclusion warning.

Awaiting you: chosen stack, ledger field mapping, trusted auth-context mechanism, membership-check boundary, timestamp/date representation, coverage confirmation and error format. These choices are not finalized by this packet.

Acceptance request: confirm the interface and map the fixture to the ledger without changing its arithmetic. Record any incompatible fields before implementation. The fixture is not evidence that a live service or authorization check exists.
