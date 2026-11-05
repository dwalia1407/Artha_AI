
import pytest

from app.auth.context import AuthContext
from app.integrations import finance


def test_adapter_returns_exact_service_result_unchanged(app, alice):
    household_id = alice.household()
    auth_context = AuthContext(
        user_id=alice.user["id"],
        email_verified=True
    )

    expected = {
        "household_id": household_id,
        "month": "2026-11",
        "currency": "INR",
        "income_minor": 5000000000000001,
        "expense_minor": 1250000000000001,
        "cash_surplus_minor": 3750000000000000,
        "transaction_count": 5,
        "coverage_status": "complete",
        "warnings": [],
        "calculation_version": "v1"
    }

    received = {}

    def mock_service(context, hid, month):
        received["context"] = context
        received["household_id"] = hid
        received["month"] = month
        return expected

    finance.register_service(mock_service)

    with app.app_context():
        result = finance.get_monthly_summary(
            auth_context, household_id, "2026-11"
        )

    assert result is expected
    assert received["context"] is auth_context
    assert received["household_id"] == household_id
    assert received["month"] == "2026-11"
    assert result["income_minor"] == 5000000000000001
    assert result["expense_minor"] == 1250000000000001


def test_adapter_propagates_service_exception_unchanged(app, alice):
    household_id = alice.household()
    auth_context = AuthContext(
        user_id=alice.user["id"],
        email_verified=True
    )

    expected_error = RuntimeError("Finance service unavailable")

    def failing_service(context, hid, month):
        raise expected_error

    finance.register_service(failing_service)

    with app.app_context():
        with pytest.raises(RuntimeError) as exc_info:
            finance.get_monthly_summary(
                auth_context, household_id, "2026-11"
            )

    assert exc_info.value is expected_error
