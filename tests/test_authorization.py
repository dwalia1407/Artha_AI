import pytest

from app.extensions import db
from app.models import HouseholdMembership
from tests.conftest import csv_text

SAMPLE = csv_text(["2026-11-01,Salary,50000.00,credit,income,",
                   "2026-11-02,Rent,10000.00,debit,purchase,Housing/Rent"])


def setup_a(alice):
    hid = alice.household("Alice home")
    acc = alice.account(hid)
    imp = alice.upload(acc, SAMPLE).get_json()["import"]["id"]
    rows = alice.rows(imp)
    approved = alice.post("/staged/approve", {"ids": [rows[0]["id"]]}).get_json()["results"][0]
    return hid, acc, imp, rows, approved["transaction_id"]


def test_user_a_can_access_own_household(alice):
    hid, acc, imp, rows, txn = setup_a(alice)
    assert alice.get("/households/" + hid).status_code == 200
    assert alice.get("/households/%s/accounts" % hid).status_code == 200
    assert alice.get("/transactions/" + txn).status_code == 200


def test_user_b_cannot_touch_household_a_by_changing_ids(alice, bob):
    hid, acc, imp, rows, txn = setup_a(alice)
    pending = rows[1]["id"]
    checks = [
        bob.get("/households/" + hid),
        bob.get("/households/%s/accounts" % hid),
        bob.post("/households/%s/accounts" % hid, {"account_name": "Evil", "account_type": "savings"}),
        bob.patch("/accounts/" + acc, {"account_name": "Evil"}),
        bob.upload(acc, SAMPLE),
        bob.get("/households/%s/imports" % hid),
        bob.get("/imports/" + imp),
        bob.get("/imports/%s/rows" % imp),
        bob.patch("/staged/" + pending, {"description": "x"}),
        bob.post("/staged/%s/reject" % pending),
        bob.get("/households/%s/transactions" % hid),
        bob.get("/transactions/" + txn),
        bob.patch("/transactions/" + txn, {"category": "Travel"}),
        bob.get("/households/%s/summary?month=2026-11" % hid),
    ]
    for r in checks:
        assert r.status_code == 404, (r.request.path, r.status_code)
    # Approval by ids of another household reports not found per row and changes nothing.
    result = bob.post("/staged/approve", {"ids": [pending]}).get_json()["results"][0]
    assert result["ok"] is False
    assert alice.rows(imp, "pending")[0]["id"] == pending
    assert alice.get("/imports/" + imp).get_json()["import"]["stats"]["approved"] == 1


def test_bob_household_list_does_not_include_alice(alice, bob):
    setup_a(alice)
    assert bob.get("/households").get_json()["households"] == []


def add_member(app, household_id, user_id, role, status="active"):
    with app.app_context():
        db.session.add(HouseholdMembership(household_id=household_id, user_id=user_id, role=role, membership_status=status))
        db.session.commit()


def test_viewer_can_read_but_not_write(app, alice, bob):
    hid, acc, imp, rows, txn = setup_a(alice)
    add_member(app, hid, bob.user["id"], "viewer")
    assert bob.get("/households/" + hid).status_code == 200
    assert bob.get("/transactions/" + txn).status_code == 200
    assert bob.get("/imports/%s/rows" % imp).status_code == 200
    assert bob.post("/households/%s/accounts" % hid, {"account_name": "N", "account_type": "savings"}).status_code == 403
    assert bob.patch("/accounts/" + acc, {"account_name": "N"}).status_code == 403
    assert bob.upload(acc, csv_text(["2026-11-05,X,1.00,debit,purchase,"])).status_code == 403
    assert bob.patch("/staged/" + rows[1]["id"], {"description": "x"}).status_code == 403
    assert bob.post("/staged/%s/reject" % rows[1]["id"]).status_code == 403
    res = bob.post("/staged/approve", {"ids": [rows[1]["id"]]}).get_json()["results"][0]
    assert res["ok"] is False
    assert bob.patch("/transactions/" + txn, {"category": "Travel"}).status_code == 403


def test_removed_member_loses_access(app, alice, bob):
    hid = alice.household()
    add_member(app, hid, bob.user["id"], "viewer", status="removed")
    assert bob.get("/households/" + hid).status_code == 404


def test_web_pages_enforce_membership(app, alice, bob):
    hid, acc, imp, rows, txn = setup_a(alice)
    c = bob.client
    for url in ["/households/" + hid, "/households/%s/ledger" % hid, "/imports/" + imp,
                "/staged/" + rows[0]["id"], "/transactions/" + txn, "/households/%s/summary" % hid]:
        assert c.get(url).status_code == 404, url
    assert c.post("/accounts/%s/imports" % acc, data={}).status_code in (302, 404)
    assert c.post("/imports/%s/approve" % imp, data={"ids": [rows[1]["id"]]}).status_code == 404


def test_owner_pages_render(alice):
    hid, acc, imp, rows, txn = setup_a(alice)
    c = alice.client
    for url in ["/dashboard", "/profile", "/households/" + hid, "/households/%s/imports" % hid,
                "/imports/" + imp, "/imports/%s?status=pending" % imp, "/staged/" + rows[1]["id"],
                "/households/%s/ledger" % hid, "/households/%s/ledger?month=2026-11" % hid,
                "/transactions/" + txn, "/households/%s/summary?month=2026-11" % hid]:
        r = c.get(url)
        assert r.status_code == 200, url
    page = c.get("/imports/" + imp).get_data(as_text=True)
    assert "50,000.00" in page and "pending" in page


def test_page_escapes_malicious_description(alice):
    hid = alice.household()
    acc = alice.account(hid)
    evil = '<script>alert(1)</script>'
    imp = alice.upload(acc, csv_text(['2026-11-01,"%s",5.00,debit,purchase,' % evil])).get_json()["import"]["id"]
    page = alice.client.get("/imports/" + imp).get_data(as_text=True)
    assert evil not in page and "&lt;script&gt;" in page
