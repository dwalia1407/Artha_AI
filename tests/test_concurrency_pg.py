"""Needs real PostgreSQL (row locks). Skipped on SQLite."""

import threading

import pytest

from app.imports import review
from app.models import Transaction
from tests.conftest import csv_text


def test_simultaneous_approval_creates_one_ledger_row(app, alice, db_url):
    if not db_url.startswith("postgres"):
        pytest.skip("needs PostgreSQL")
    hid = alice.household()
    acc = alice.account(hid)
    imp = alice.upload(acc, csv_text(["2026-11-01,Pay,10.00,credit,income,"])).get_json()["import"]["id"]
    row_id = alice.rows(imp)[0]["id"]
    barrier = threading.Barrier(2)
    outcomes = []

    def worker():
        with app.app_context():
            barrier.wait()
            outcomes.append(review.approve_staged(alice.user["id"], [row_id])[0]["ok"])

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == [False, True]
    with app.app_context():
        assert Transaction.query.count() == 1
