"""
Ledger-to-finance-contract tests.

The summary arithmetic here comes from tests/doubles/reference_summary.py,
a TEST DOUBLE written from docs/contracts.md. These tests show the ledger can
express the contract and feed it correctly; they do not test Disha's service.
"""

import json
from pathlib import Path

import pytest

from app.auth.context import AuthContext
from app.errors import InvalidRequest, NotFound, ServiceUnavailable, Unauthenticated
from app.integrations import finance
from app.models import User
from tests.conftest import csv_text
from tests.doubles.reference_summary import make_reference_service

FIXTURE = Path("docs/handoffs/Biswa/day_01_2026-11-01/monthly_summary_fixture.json")


def ctx_for(app, api):
    return AuthContext(user_id=api.user["id"], email_verified=False)


def import_and_approve(alice, rows, matched=None):
    hid = alice.household()
    acc = alice.account(hid)
    imp = alice.upload(acc, csv_text(rows)).get_json()["import"]["id"]
    ids = {r["original_description"]: r["id"] for r in alice.rows(imp)}
    results = alice.post("/staged/approve", {"ids": list(ids.values())}).get_json()["results"]
    assert all(r["ok"] for r in results), results
    return hid, acc, imp, {d: r["transaction_id"] for d, r in zip(ids, results)}


def test_fixture_values_match_the_spec():
    data = json.loads(FIXTURE.read_text())
    exp = data["expected_response"]
    assert (exp["income_minor"], exp["expense_minor"], exp["cash_surplus_minor"]) == (5000000, 1250000, 3750000)
    assert exp["transaction_count"] == 5 and exp["coverage_status"] == "complete"
    assert exp["warnings"] == [] and exp["calculation_version"] == "v1"


def test_fixture_flows_through_real_import_and_approval(app, alice):
    data = json.loads(FIXTURE.read_text())
    hid = alice.household()
    acc = alice.account(hid)
    cat = {"Groceries": "Groceries", "Housing/Rent": "Housing/Rent"}
    lines = []
    for r in data["records"]:
        if r["type"] == "refund":
            continue
        direction = "credit" if r["type"] == "income" else "debit"
        if r["type"] == "internal_transfer":
            direction = "debit"
        lines.append('%s,%s,%s,%s,%s,%s' % (r["date"], r["transaction_id"], "%d.%02d" % divmod(r["amount_minor"], 100),
                                            direction, r["type"], cat.get(r.get("category"), "")))
    refund = [r for r in data["records"] if r["type"] == "refund"][0]
    lines.append('%s,%s,%s,credit,refund,' % (refund["date"], refund["transaction_id"], "%d.%02d" % divmod(refund["amount_minor"], 100)))
    imp = alice.upload(acc, csv_text(lines)).get_json()["import"]["id"]
    rows = {r["original_description"]: r["id"] for r in alice.rows(imp)}

    non_refund = [i for d, i in rows.items() if d != "refund-1"]
    res = alice.post("/staged/approve", {"ids": non_refund}).get_json()["results"]
    assert all(r["ok"] for r in res)
    purchase_txn = dict(zip([d for d in rows if d != "refund-1"], [r["transaction_id"] for r in res]))["groceries-1"]
    alice.patch("/staged/" + rows["refund-1"], {"matched_transaction_id": purchase_txn})
    assert alice.post("/staged/approve", {"ids": [rows["refund-1"]]}).get_json()["results"][0]["ok"]

    finance.register_service(make_reference_service(coverage_confirmed=True))
    got = alice.get("/households/%s/summary?month=2026-11" % hid).get_json()
    expected = dict(data["expected_response"], household_id=hid)
    assert got == expected


def summary(app, alice, hid, month="2026-11", **kw):
    finance.register_service(make_reference_service(**kw))
    return finance.get_monthly_summary(ctx_for(app, alice), hid, month)


def test_no_data_is_unknown_not_zero(app, alice):
    hid = alice.household()
    with app.app_context():
        got = summary(app, alice, hid)
    assert got["income_minor"] is None and got["expense_minor"] is None and got["cash_surplus_minor"] is None
    assert got["transaction_count"] == 0


def test_pending_and_rejected_rows_are_excluded(app, alice):
    hid = alice.household()
    acc = alice.account(hid)
    imp = alice.upload(acc, csv_text(["2026-11-01,Pay,1000.00,credit,income,", "2026-11-01,Pend,500.00,debit,purchase,",
                                      "2026-11-01,Rej,700.00,debit,purchase,"])).get_json()["import"]["id"]
    rows = {r["original_description"]: r["id"] for r in alice.rows(imp)}
    alice.post("/staged/%s/reject" % rows["Rej"])
    alice.post("/staged/approve", {"ids": [rows["Pay"]]})
    with app.app_context():
        got = summary(app, alice, hid)
    assert (got["income_minor"], got["expense_minor"], got["transaction_count"]) == (100000, 0, 1)


def test_transfer_card_settlement_cash_investment_loan(app, alice):
    hid, acc, imp, ids = import_and_approve(alice, [
        "2026-11-01,Salary,1000.00,credit,income,",
        "2026-11-02,Shop,100.00,debit,purchase,Shopping & Clothing",
        "2026-11-03,Move to savings,300.00,debit,internal_transfer,",
        "2026-11-04,Card bill,100.00,debit,card_settlement,",
        "2026-11-05,ATM,50.00,debit,cash_withdrawal,",
        "2026-11-06,Mutual fund,200.00,debit,investment,",
        "2026-11-07,Home loan EMI,400.00,debit,loan_payment,",
    ])
    with app.app_context():
        got = summary(app, alice, hid)
        assert (got["income_minor"], got["expense_minor"], got["cash_surplus_minor"]) == (100000, 10000, 90000)
        assert got["transaction_count"] == 7
        assert any("Debt payments" in w for w in got["warnings"]) and got["coverage_status"] == "partial"
        incomplete = summary(app, alice, hid, card_purchases_recorded=False)
        assert any("Card settlement" in w for w in incomplete["warnings"])


def test_unmatched_refund_is_excluded_with_warning(app, alice):
    hid, acc, imp, ids = import_and_approve(alice, ["2026-11-01,Shop,100.00,debit,purchase,",
                                                    "2026-11-05,Refund,30.00,credit,refund,"])
    with app.app_context():
        got = summary(app, alice, hid)
    assert got["expense_minor"] == 10000 and any("refund" in w.lower() for w in got["warnings"])


def test_refund_reduces_expense_in_month_received_only(app, alice):
    hid, acc, imp, ids = import_and_approve(alice, ["2026-10-30,Shop,100.00,debit,purchase,"])
    purchase = ids["Shop"]
    imp2 = alice.upload(acc, csv_text(["2026-11-02,Refund,30.00,credit,refund,"])).get_json()["import"]["id"]
    row = alice.rows(imp2)[0]
    alice.patch("/staged/" + row["id"], {"matched_transaction_id": purchase})
    alice.post("/staged/approve", {"ids": [row["id"]]})
    with app.app_context():
        october = summary(app, alice, hid, month="2026-10")
        november = summary(app, alice, hid, month="2026-11")
    assert october["expense_minor"] == 10000
    assert november["expense_minor"] == -3000


def test_month_boundaries_use_calendar_dates(app, alice):
    hid, acc, imp, ids = import_and_approve(alice, ["2026-10-31,Last,1.00,debit,purchase,", "2026-11-01,First,2.00,debit,purchase,",
                                                    "2026-11-30,End,3.00,debit,purchase,", "2026-12-01,Next,4.00,debit,purchase,"])
    with app.app_context():
        assert summary(app, alice, hid)["expense_minor"] == 500
        assert summary(app, alice, hid, month="2026-12")["transaction_count"] == 1
    rows = alice.get("/households/%s/transactions?month=2026-11" % hid).get_json()
    assert rows["total"] == 2


def test_refund_match_must_be_in_same_household(alice, bob):
    hid, acc, imp, ids = import_and_approve(alice, ["2026-11-01,Shop,100.00,debit,purchase,"])
    bh = bob.household()
    bacc = bob.account(bh)
    bimp = bob.upload(bacc, csv_text(["2026-11-02,Refund,10.00,credit,refund,"])).get_json()["import"]["id"]
    row = bob.rows(bimp)[0]
    r = bob.patch("/staged/" + row["id"], {"matched_transaction_id": ids["Shop"]}).get_json()["row"]
    assert r["status"] == "invalid" and "not found in this household" in r["validation_errors"][0]["message"]


def test_gateway_requires_trusted_context_membership_and_service(app, alice, bob):
    hid = alice.household()
    with app.app_context():
        with pytest.raises(Unauthenticated):
            finance.get_monthly_summary({"user_id": alice.user["id"]}, hid, "2026-11")
        with pytest.raises(Unauthenticated):
            finance.get_monthly_summary(None, hid, "2026-11")
        with pytest.raises(InvalidRequest):
            finance.get_monthly_summary(ctx_for(app, alice), hid, "2026-13")
        with pytest.raises(InvalidRequest):
            finance.get_monthly_summary(ctx_for(app, alice), "", "2026-11")
        with pytest.raises(ServiceUnavailable):
            finance.get_monthly_summary(ctx_for(app, alice), hid, "2026-11")
        finance.register_service(make_reference_service())
        with pytest.raises(NotFound):
            finance.get_monthly_summary(ctx_for(app, bob), hid, "2026-11")
        assert finance.get_monthly_summary(ctx_for(app, alice), hid, "2026-11")["household_id"] == hid


def test_summary_endpoint_when_service_not_connected(alice):
    hid = alice.household()
    r = alice.get("/households/%s/summary?month=2026-11" % hid)
    assert r.status_code == 503 and r.get_json()["error"]["code"] == "service_unavailable"
    page = alice.client.get("/households/%s/summary?month=2026-11" % hid).get_data(as_text=True)
    assert "not connected" in page and "0.00" not in page


def test_feed_requires_membership(app, alice, bob):
    from app.ledger.service import approved_records_for_month
    hid = alice.household()
    with app.app_context():
        with pytest.raises(NotFound):
            approved_records_for_month(ctx_for(app, bob), hid, "2026-11")
