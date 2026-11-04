"""
Ledger reads and post-approval corrections.

This module does no financial arithmetic. Totals come from the finance
service (see app/integrations/finance.py); this module only lists approved
records and feeds them to that service.
"""

import re
from datetime import date

from app.constants import CATEGORIES, TRANSACTION_TYPES
from app.errors import InvalidRequest, NotFound
from app.extensions import db
from app.households.service import require_member
from app.imports.csv_parser import type_direction_error
from app.imports.review import check_matched_id, now_iso
from app.models import Transaction

MONTH_RE = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def month_bounds(month):
    """Return (first day, first day of next month) for 'YYYY-MM'. Dates are Asia/Kolkata calendar dates."""
    match = MONTH_RE.match(month or "")
    if not match:
        raise InvalidRequest("Month must look like 2026-11")
    year, mon = int(match.group(1)), int(match.group(2))
    start = date(year, mon, 1)
    end = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    return start, end


def list_transactions(actor_id, household_id, month=None, account_id=None,
                      transaction_type=None, category=None, limit=200, offset=0):
    require_member(actor_id, household_id)
    query = Transaction.query.filter_by(household_id=household_id)
    if month:
        start, end = month_bounds(month)
        query = query.filter(Transaction.transaction_date >= start, Transaction.transaction_date < end)
    if account_id:
        query = query.filter_by(account_id=account_id)
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    if category:
        query = query.filter_by(category=category)
    total = query.count()
    rows = (query.order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
            .limit(min(max(limit, 1), 500)).offset(max(offset, 0)).all())
    return rows, total


def get_transaction(actor_id, transaction_id):
    txn = db.session.get(Transaction, transaction_id) if transaction_id else None
    if txn is None:
        raise NotFound("Transaction not found")
    try:
        require_member(actor_id, txn.household_id)
    except NotFound:
        raise NotFound("Transaction not found")
    return txn


def correct_transaction(actor_id, transaction_id, changes):
    """
    Correct classification fields of an approved record and keep the history.
    Amount, date and direction are not editable here: re-import the statement.
    """
    txn = get_transaction(actor_id, transaction_id)
    require_member(actor_id, txn.household_id, write=True)
    allowed = ("category", "transaction_type", "matched_transaction_id", "description")
    unknown = [k for k in changes if k not in allowed]
    if unknown:
        raise InvalidRequest("Cannot correct: " + ", ".join(unknown))

    new = {"category": txn.category, "transaction_type": txn.transaction_type,
           "matched_transaction_id": txn.matched_transaction_id, "description": txn.description}
    for key, value in changes.items():
        new[key] = (value or "").strip() or None
    if new["category"] is not None and new["category"] not in CATEGORIES:
        raise InvalidRequest("Unknown category")
    if new["transaction_type"] not in TRANSACTION_TYPES:
        raise InvalidRequest("Unknown transaction type")
    if not new["description"]:
        raise InvalidRequest("Description cannot be empty")
    message = type_direction_error(new["transaction_type"], txn.direction)
    if message:
        raise InvalidRequest(message)
    if new["matched_transaction_id"]:
        if new["matched_transaction_id"] == txn.id:
            raise InvalidRequest("A transaction cannot be matched to itself")
        message = check_matched_id(txn.household_id, new["matched_transaction_id"])
        if message:
            raise InvalidRequest(message)

    history = list(txn.correction_metadata or [])
    for key in changes:
        old_value = getattr(txn, key)
        if old_value != new[key]:
            history.append({"at": now_iso(), "by": actor_id, "stage": "ledger",
                            "field": key, "old": old_value, "new": new[key]})
            setattr(txn, key, new[key])
    txn.correction_metadata = history
    db.session.commit()
    return txn


def approved_records_for_month(auth_context, household_id, month):
    """
    Read-only feed for the finance service: approved records of one month.
    Requires a trusted AuthContext and active membership. Rejected, pending
    and invalid rows are not in the ledger table, so they cannot appear here.
    """
    require_member(auth_context.user_id, household_id)
    start, end = month_bounds(month)
    rows = (Transaction.query.filter(Transaction.household_id == household_id,
                                     Transaction.transaction_date >= start,
                                     Transaction.transaction_date < end)
            .order_by(Transaction.transaction_date, Transaction.created_at).all())
    return [{"transaction_id": t.id, "date": t.transaction_date.isoformat(),
             "type": t.transaction_type, "category": t.category, "direction": t.direction,
             "amount_minor": t.amount_minor, "currency": t.currency,
             "matched_transaction_id": t.matched_transaction_id, "approved": True} for t in rows]
