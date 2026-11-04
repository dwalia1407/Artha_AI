from app.extensions import db
from app.models import Import, StagedTransaction, Transaction
from tests.conftest import csv_text

GOOD = csv_text(["2026-11-01,Salary,50000.00,credit,income,",
                 "2026-11-01,Groceries,3000.00,debit,purchase,Groceries",
                 "2026-11-02,Mystery,10.00,debit,,"])


def setup(alice):
    hid = alice.household()
    return hid, alice.account(hid)


def ledger_count(app):
    with app.app_context():
        return Transaction.query.count()


def test_upload_stages_rows_and_ledger_stays_empty(app, alice):
    hid, acc = setup(alice)
    r = alice.upload(acc, GOOD)
    assert r.status_code == 201
    body = r.get_json()
    assert body["already_imported"] is False
    assert body["import"]["total_rows"] == 3 and body["import"]["parser_version"] == "csv-v1"
    assert body["import"]["stats"]["pending"] == 3
    assert ledger_count(app) == 0
    assert alice.get("/households/%s/transactions" % hid).get_json()["total"] == 0


def test_invalid_rows_are_listed_with_row_errors(app, alice):
    hid, acc = setup(alice)
    text = csv_text(["2026-13-01,Bad date,5,debit,purchase,", "2026-11-01,Good,5,debit,purchase,",
                     "2026-11-01,USD thing,5 USD,debit,purchase,"])
    imp = alice.upload(acc, text).get_json()["import"]
    assert imp["valid_rows"] == 1 and imp["invalid_rows"] == 2
    invalid = alice.rows(imp["id"], "invalid")
    assert len(invalid) == 2 and invalid[0]["validation_errors"][0]["field"] == "date"
    assert invalid[0]["source_row_number"] == 2


def test_upload_rejections(app, alice):
    hid, acc = setup(alice)
    assert alice.upload(acc, GOOD, filename="stmt.txt").status_code == 400
    assert alice.upload(acc, b"").status_code == 400
    assert alice.upload(acc, "date,description\n2026-11-01,x\n").status_code == 400
    assert alice.upload(acc, b"\x00\x01binary", filename="x.csv").status_code == 400
    assert alice.upload(acc, GOOD, layout="nope").status_code == 400
    app.config["MAX_UPLOAD_BYTES"] = 50
    app.config["MAX_CONTENT_LENGTH"] = 50 + 64 * 1024
    assert alice.upload(acc, GOOD).status_code == 400
    app.config["MAX_CONTENT_LENGTH"] = 1000
    assert alice.upload(acc, b"x" * 5000).status_code == 413
    with app.app_context():
        assert Import.query.filter_by(import_status="staged").count() == 0


def test_failed_file_is_recorded_and_retry_allowed(app, alice):
    hid, acc = setup(alice)
    bad = "date,description\n2026-11-01,x\n"
    assert alice.upload(acc, bad).status_code == 400
    assert alice.upload(acc, bad).status_code == 400
    history = alice.get("/households/%s/imports" % hid).get_json()["imports"]
    assert [i["import_status"] for i in history] == ["failed", "failed"]
    assert "Missing required column" in history[0]["error_message"]


def test_filename_path_is_stripped(alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD, filename="..\\..\\etc/evil.csv").get_json()["import"]
    assert imp["filename"] == "evil.csv"


def test_edit_fixes_invalid_row_and_records_history(alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, csv_text(["2026-13-01,Rent,1000.00,debit,purchase,"])).get_json()["import"]["id"]
    row = alice.rows(imp)[0]
    assert row["status"] == "invalid"
    fixed = alice.patch("/staged/" + row["id"], {"date": "2026-11-03", "amount": "1,250.50",
                                                 "description": "Rent Nov", "category": "Housing/Rent"}).get_json()["row"]
    assert fixed["status"] == "pending" and fixed["amount_minor"] == 125050
    assert fixed["transaction_date"] == "2026-11-03" and fixed["original_description"] == "Rent"
    still_bad = alice.patch("/staged/" + row["id"], {"amount": "abc"})
    assert still_bad.get_json()["row"]["status"] == "invalid"
    assert alice.patch("/staged/" + row["id"], {"nonsense": "1"}).status_code == 400


def test_type_direction_rules(alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, csv_text(["2026-11-01,Pay,10.00,debit,income,"])).get_json()["import"]["id"]
    row = alice.rows(imp)[0]
    assert row["status"] == "invalid"
    assert "must be a credit" in row["validation_errors"][0]["message"]
    ok = alice.patch("/staged/" + row["id"], {"direction": "credit"}).get_json()["row"]
    assert ok["status"] == "pending"


def test_approval_requires_type_and_valid_row(app, alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD + "2026-13-45,Bad,1,debit,purchase,\n").get_json()["import"]["id"]
    rows = {r["original_description"]: r for r in alice.rows(imp)}
    res = alice.post("/staged/approve", {"ids": [rows["Mystery"]["id"], rows["Bad"]["id"]]}).get_json()["results"]
    assert [r["ok"] for r in res] == [False, False]
    assert "transaction type" in res[0]["error"] and "validation" in res[1]["error"]
    assert ledger_count(app) == 0
    ok = alice.patch("/staged/" + rows["Mystery"]["id"], {"type": "purchase"}).get_json()["row"]
    assert alice.post("/staged/approve", {"ids": [ok["id"]]}).get_json()["results"][0]["ok"] is True


def test_approve_persists_with_provenance_and_corrections(app, alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD).get_json()["import"]["id"]
    row = [r for r in alice.rows(imp) if r["original_description"] == "Groceries"][0]
    alice.patch("/staged/" + row["id"], {"description": "Big Bazaar", "category": "Shopping & Clothing"})
    tid = alice.post("/staged/approve", {"ids": [row["id"]]}).get_json()["results"][0]["transaction_id"]
    t = alice.get("/transactions/" + tid).get_json()["transaction"]
    assert t["import_id"] == imp and t["source_row_number"] == 3
    assert t["original_description"] == "Groceries" and t["description"] == "Big Bazaar"
    assert t["amount_minor"] == 300000 and t["currency"] == "INR" and t["approval_status"] == "approved"
    assert {c["field"] for c in t["correction_metadata"]} == {"description", "category"}
    assert alice.get("/imports/" + imp).get_json()["import"]["stats"]["approved"] == 1


def test_duplicate_approval_creates_one_ledger_row(app, alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD).get_json()["import"]["id"]
    rid = alice.rows(imp)[0]["id"]
    first = alice.post("/staged/approve", {"ids": [rid, rid]}).get_json()["results"]
    assert [r["ok"] for r in first] == [True, False]
    again = alice.post("/staged/approve", {"ids": [rid]}).get_json()["results"]
    assert again[0]["ok"] is False
    assert ledger_count(app) == 1


def test_ledger_unique_row_constraint_is_a_backstop(app, alice):
    import pytest
    from sqlalchemy.exc import IntegrityError
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD).get_json()["import"]["id"]
    alice.post("/staged/approve", {"ids": [alice.rows(imp)[0]["id"]]})
    with app.app_context():
        t = Transaction.query.first()
        clone = Transaction(household_id=t.household_id, account_id=t.account_id, import_id=t.import_id,
                            source_row_number=t.source_row_number, amount_minor=1, direction="debit",
                            transaction_date=t.transaction_date, original_description="x", description="x",
                            transaction_type="purchase")
        db.session.add(clone)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_rejected_rows_never_enter_ledger_and_can_be_reopened(app, alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD).get_json()["import"]["id"]
    rid = alice.rows(imp)[0]["id"]
    assert alice.post("/staged/%s/reject" % rid).get_json()["row"]["status"] == "rejected"
    assert alice.post("/staged/approve", {"ids": [rid]}).get_json()["results"][0]["ok"] is False
    assert alice.patch("/staged/" + rid, {"description": "x"}).status_code == 409
    assert ledger_count(app) == 0
    assert alice.post("/staged/%s/reopen" % rid).get_json()["row"]["status"] == "pending"
    assert alice.post("/staged/approve", {"ids": [rid]}).get_json()["results"][0]["ok"] is True
    assert alice.post("/staged/%s/reject" % rid).status_code == 409


def test_import_completes_when_nothing_pending(app, alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, csv_text(["2026-11-01,A,1.00,debit,purchase,"])).get_json()["import"]["id"]
    rid = alice.rows(imp)[0]["id"]
    alice.post("/staged/%s/reject" % rid)
    assert alice.get("/imports/" + imp).get_json()["import"]["import_status"] == "completed"
    alice.post("/staged/%s/reopen" % rid)
    assert alice.get("/imports/" + imp).get_json()["import"]["import_status"] == "staged"


def test_ledger_correction_keeps_history_and_blocks_bad_values(alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, GOOD).get_json()["import"]["id"]
    tid = alice.post("/staged/approve", {"ids": [alice.rows(imp)[1]["id"]]}).get_json()["results"][0]["transaction_id"]
    t = alice.patch("/transactions/" + tid, {"category": "Travel"}).get_json()["transaction"]
    assert t["category"] == "Travel" and t["correction_metadata"][-1]["old"] == "Groceries"
    assert alice.patch("/transactions/" + tid, {"category": "Made up"}).status_code == 400
    assert alice.patch("/transactions/" + tid, {"transaction_type": "income"}).status_code == 400
    assert alice.patch("/transactions/" + tid, {"amount_minor": 1}).status_code == 400
    assert alice.patch("/transactions/" + tid, {"matched_transaction_id": tid}).status_code == 400


# Idempotency and duplicates

def test_exact_reimport_is_idempotent(app, alice):
    hid, acc = setup(alice)
    first = alice.upload(acc, GOOD).get_json()["import"]
    alice.post("/staged/approve", {"ids": [r["id"] for r in alice.rows(first["id"])[:2]]})
    again = alice.upload(acc, GOOD)
    assert again.status_code == 200 and again.get_json()["already_imported"] is True
    assert again.get_json()["import"]["id"] == first["id"]
    with app.app_context():
        assert Import.query.count() == 1
        assert StagedTransaction.query.count() == 3
        assert Transaction.query.count() == 2


def test_same_file_to_different_account_is_a_new_import(alice):
    hid, acc = setup(alice)
    other = alice.account(hid, "Second")
    a = alice.upload(acc, GOOD).get_json()["import"]["id"]
    b = alice.upload(other, GOOD).get_json()["import"]["id"]
    assert a != b


def test_overlapping_statement_flags_possible_duplicates(app, alice):
    hid, acc = setup(alice)
    first = alice.upload(acc, GOOD).get_json()["import"]["id"]
    alice.post("/staged/approve", {"ids": [r["id"] for r in alice.rows(first)[:2]]})
    overlap = csv_text(["2026-11-01,Salary,50000.00,credit,income,",
                        "2026-11-01,GROCERIES,3000.00,debit,purchase,Groceries",
                        "2026-11-05,New thing,20.00,debit,purchase,"])
    imp = alice.upload(acc, overlap).get_json()["import"]
    rows = alice.rows(imp["id"])
    assert [r["potential_duplicate"] for r in rows] == [True, True, False]
    assert imp["stats"]["potential_duplicates_pending"] == 2
    blocked = alice.post("/staged/approve", {"ids": [rows[0]["id"]]}).get_json()["results"][0]
    assert blocked["ok"] is False and "duplicate" in blocked["error"].lower()
    allowed = alice.post("/staged/approve", {"ids": [rows[0]["id"]], "confirm_duplicates": True}).get_json()["results"][0]
    assert allowed["ok"] is True
    with app.app_context():
        assert Transaction.query.count() == 3


def test_repeated_purchases_in_one_file_are_not_flagged_and_stay(app, alice):
    hid, acc = setup(alice)
    text = csv_text(["2026-11-01,Chai,20.00,debit,purchase,Eating Out"] * 3)
    imp = alice.upload(acc, text).get_json()["import"]["id"]
    rows = alice.rows(imp)
    assert not any(r["potential_duplicate"] for r in rows)
    res = alice.post("/staged/approve", {"ids": [r["id"] for r in rows]}).get_json()["results"]
    assert all(r["ok"] for r in res) and ledger_count(app) == 3


def test_overlap_counts_are_multiset_aware(app, alice):
    hid, acc = setup(alice)
    one = "2026-11-01,Chai,20.00,debit,purchase,Eating Out"
    first = alice.upload(acc, csv_text([one, one])).get_json()["import"]["id"]
    alice.post("/staged/approve", {"ids": [r["id"] for r in alice.rows(first)]})
    second = alice.upload(acc, csv_text([one, one, one])).get_json()["import"]["id"]
    assert [r["potential_duplicate"] for r in alice.rows(second)] == [True, True, False]


def test_pending_rows_of_other_import_also_flag(alice):
    hid, acc = setup(alice)
    alice.upload(acc, csv_text(["2026-11-01,Chai,20.00,debit,purchase,"]))
    second = alice.upload(acc, csv_text(["2026-11-01,Chai,20.00,debit,purchase,", "2026-11-09,x,1.00,debit,purchase,"])).get_json()["import"]["id"]
    assert alice.rows(second)[0]["potential_duplicate"] is True


def test_bulk_set_type_via_web(app, alice):
    hid, acc = setup(alice)
    imp = alice.upload(acc, csv_text(["2026-11-01,A,5.00,debit,,", "2026-11-01,B,6.00,debit,,"])).get_json()["import"]["id"]
    ids = [r["id"] for r in alice.rows(imp)]
    r = alice.client.post("/imports/%s/set-type" % imp, data={"ids": ids, "type": "purchase"})
    assert r.status_code == 302
    assert all(x["transaction_type"] == "purchase" for x in alice.rows(imp))
    r = alice.client.post("/imports/%s/approve" % imp, data={"ids": ids})
    assert ledger_count(app) == 2


def test_web_upload_flow(alice):
    import io
    hid, acc = setup(alice)
    r = alice.client.post("/accounts/%s/imports" % acc, data={"file": (io.BytesIO(GOOD.encode()), "s.csv"), "layout": "signed_amount"},
                          content_type="multipart/form-data")
    assert r.status_code == 302 and "/imports/" in r.headers["Location"]
    page = alice.client.get(r.headers["Location"]).get_data(as_text=True)
    assert "Pending review" in page and "Salary" in page
