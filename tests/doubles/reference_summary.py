"""
TEST DOUBLE. This is NOT Disha's finance service.

It follows the approved treatment table in docs/contracts.md only so the
ledger can be shown to express the contract fixture and the semantic cases.
It is never registered outside tests. Coverage status values other than
"complete" are placeholders because the real enum is still pending.
"""

from app.ledger.service import approved_records_for_month


def make_reference_service(coverage_confirmed=True, card_purchases_recorded=True):
    def service(auth_context, household_id, month):
        records = approved_records_for_month(auth_context, household_id, month)
        warnings = []
        if not records:
            return {"household_id": household_id, "month": month, "currency": "INR",
                    "income_minor": None, "expense_minor": None, "cash_surplus_minor": None,
                    "transaction_count": 0, "coverage_status": "unknown",
                    "warnings": ["No approved records for this month"], "calculation_version": "test-double"}
        income = 0
        expense = 0
        for r in records:
            t, amount = r["type"], r["amount_minor"]
            if t == "income":
                income += amount
            elif t in ("purchase", "fee"):
                expense += amount
            elif t == "refund":
                if r["matched_transaction_id"]:
                    expense -= amount
                else:
                    warnings.append("Unmatched refund excluded pending review")
            elif t == "card_settlement":
                if not card_purchases_recorded:
                    warnings.append("Card settlement without recorded purchases: coverage incomplete")
            elif t == "loan_payment":
                warnings.append("Debt payments are excluded from income and expenses")
            # internal_transfer, cash_withdrawal, investment: kept out of totals
        status = "complete" if coverage_confirmed and not warnings else "partial"
        if not coverage_confirmed:
            warnings.append("Coverage not confirmed")
        return {"household_id": household_id, "month": month, "currency": "INR",
                "income_minor": income, "expense_minor": expense, "cash_surplus_minor": income - expense,
                "transaction_count": len(records), "coverage_status": status,
                "warnings": warnings, "calculation_version": "v1" if status == "complete" else "test-double"}
    return service
