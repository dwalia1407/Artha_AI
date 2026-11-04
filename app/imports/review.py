"""
Review step: edit, reject, reopen and approve staged rows.

Approval is the only way a row enters the ledger. It runs inside a database
transaction and is protected by a unique (import_id, source_row_number)
constraint on the ledger so a row cannot be approved twice.
"""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.constants import (
    APPROVAL_APPROVED, APPROVAL_PENDING, APPROVAL_REJECTED, IMPORT_COMPLETED,
    IMPORT_STAGED, VALIDATION_INVALID, VALIDATION_VALID,
)
from app.errors import AppError, Conflict, InvalidRequest, NotFound
from app.extensions import db
from app.households.service import require_member
from app.imports.csv_parser import check_values, parse_amount, type_direction_error
from app.imports.service import duplicate_candidates_for_edit
from app.models import Import, StagedTransaction, Transaction

EDITABLE_FIELDS = ("description", "date", "amount", "direction", "type", "category", "matched_transaction_id")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_staged(actor_id, staged_id, write=False):
    staged = db.session.get(StagedTransaction, staged_id) if staged_id else None
    if staged is None:
        raise NotFound("Transaction not found")
    try:
        require_member(actor_id, staged.household_id, write=write)
    except NotFound:
        raise NotFound("Transaction not found")
    return staged


def check_matched_id(household_id, matched_id):
    if not matched_id:
        return None
    found = db.session.get(Transaction, matched_id)
    if found is None or found.household_id != household_id:
        return "Matched transaction was not found in this household"
    return None


def refresh_import_status(import_id):
    imp = db.session.get(Import, import_id)
    pending = StagedTransaction.query.filter_by(import_id=import_id, approval_status=APPROVAL_PENDING).count()
    imp.import_status = IMPORT_STAGED if pending else IMPORT_COMPLETED


def edit_staged(actor_id, staged_id, changes):
    """changes: dict of text values using EDITABLE_FIELDS keys. Re-validates the whole row."""
    staged = get_staged(actor_id, staged_id, write=True)
    if staged.approval_status != APPROVAL_PENDING:
        raise Conflict("Only pending or invalid rows can be edited (reopen a rejected row first)")
    unknown = [k for k in changes if k not in EDITABLE_FIELDS]
    if unknown:
        raise InvalidRequest("Cannot edit: " + ", ".join(unknown))

    description = changes.get("description", staged.description)
    date_text = changes["date"] if "date" in changes else (staged.transaction_date.isoformat() if staged.transaction_date else "")
    direction = changes.get("direction", staged.direction)
    type_text = changes["type"] if "type" in changes else (staged.transaction_type or "")
    category_text = changes["category"] if "category" in changes else (staged.category or "")
    matched_id = (changes["matched_transaction_id"] if "matched_transaction_id" in changes
                  else staged.matched_transaction_id) or None

    amount_minor = staged.amount_minor
    extra_errors = []
    if "amount" in changes:
        try:
            amount_minor = parse_amount(changes["amount"])
            if amount_minor < 0:
                amount_minor = None
                extra_errors.append({"field": "amount", "message": "Enter the amount as a positive number and set the direction"})
        except ValueError as exc:
            amount_minor = None
            extra_errors.append({"field": "amount", "message": str(exc)})

    clean, errors = check_values(description, date_text, amount_minor, direction, staged.currency, type_text, category_text)
    if extra_errors:
        errors = [e for e in errors if e["field"] != "amount"] + extra_errors
    message = check_matched_id(staged.household_id, matched_id)
    if message:
        errors.append({"field": "matched_transaction_id", "message": message})

    old = {"description": staged.description,
           "date": staged.transaction_date.isoformat() if staged.transaction_date else None,
           "amount": staged.amount_minor, "direction": staged.direction,
           "type": staged.transaction_type, "category": staged.category,
           "matched_transaction_id": staged.matched_transaction_id}
    new = {"description": clean["description"],
           "date": clean["transaction_date"].isoformat() if clean["transaction_date"] else None,
           "amount": clean["amount_minor"], "direction": clean["direction"],
           "type": clean["transaction_type"], "category": clean["category"],
           "matched_transaction_id": matched_id}
    history = list(staged.edit_history or [])
    for field in EDITABLE_FIELDS:
        if field in changes and old[field] != new[field]:
            history.append({"at": now_iso(), "by": actor_id, "stage": "review",
                            "field": field, "old": old[field], "new": new[field]})

    staged.description = clean["description"]
    staged.transaction_date = clean["transaction_date"]
    staged.amount_minor = clean["amount_minor"]
    staged.direction = clean["direction"]
    staged.transaction_type = clean["transaction_type"]
    staged.category = clean["category"]
    staged.matched_transaction_id = matched_id
    staged.validation_errors = errors
    staged.validation_status = VALIDATION_INVALID if errors else VALIDATION_VALID
    staged.edit_history = history
    candidates = duplicate_candidates_for_edit(staged.account_id, staged) if not errors else []
    staged.potential_duplicate = bool(candidates)
    staged.duplicate_candidates = candidates
    db.session.commit()
    return staged


def reject_staged(actor_id, staged_id):
    staged = get_staged(actor_id, staged_id, write=True)
    if staged.approval_status == APPROVAL_APPROVED:
        raise Conflict("An approved row cannot be rejected here")
    staged.approval_status = APPROVAL_REJECTED
    refresh_import_status(staged.import_id)
    db.session.commit()
    return staged


def reopen_staged(actor_id, staged_id):
    staged = get_staged(actor_id, staged_id, write=True)
    if staged.approval_status != APPROVAL_REJECTED:
        raise Conflict("Only rejected rows can be reopened")
    staged.approval_status = APPROVAL_PENDING
    refresh_import_status(staged.import_id)
    db.session.commit()
    return staged


def set_type_for_rows(actor_id, staged_ids, type_text):
    """Bulk helper: give several pending rows the same transaction type (each row is re-validated)."""
    results = []
    for sid in staged_ids:
        try:
            edit_staged(actor_id, sid, {"type": type_text})
            results.append({"id": sid, "ok": True})
        except AppError as exc:
            db.session.rollback()
            results.append({"id": sid, "ok": False, "error": exc.message})
    return results


def approve_one(actor_id, staged_id, confirm_duplicate=False):
    staged = get_staged(actor_id, staged_id, write=True)
    locked = (db.session.query(StagedTransaction).filter_by(id=staged.id).with_for_update().one())
    if locked.approval_status == APPROVAL_APPROVED:
        raise Conflict("Already approved")
    if locked.approval_status == APPROVAL_REJECTED:
        raise Conflict("Rejected rows must be reopened before approval")
    if locked.validation_status != VALIDATION_VALID:
        raise InvalidRequest("Row has validation errors and cannot be approved")
    if not locked.transaction_type:
        raise InvalidRequest("Choose a transaction type before approving")
    message = type_direction_error(locked.transaction_type, locked.direction)
    if message:
        raise InvalidRequest(message)
    if locked.potential_duplicate and not confirm_duplicate:
        raise Conflict("Possible duplicate: confirm it is a legitimate separate transaction to approve")

    ledger_row = Transaction(
        household_id=locked.household_id, account_id=locked.account_id, import_id=locked.import_id,
        source_row_number=locked.source_row_number, amount_minor=locked.amount_minor,
        currency=locked.currency, direction=locked.direction, transaction_date=locked.transaction_date,
        original_description=locked.original_description, description=locked.description,
        transaction_type=locked.transaction_type, category=locked.category,
        matched_transaction_id=locked.matched_transaction_id,
        correction_metadata=list(locked.edit_history or []))
    db.session.add(ledger_row)
    db.session.flush()
    locked.approval_status = APPROVAL_APPROVED
    locked.transaction_id = ledger_row.id
    return ledger_row


def approve_staged(actor_id, staged_ids, confirm_duplicates=False):
    """
    Approve several rows. Each row is its own savepoint so one bad row does
    not block the rest. Returns a result list; nothing is silently skipped.
    """
    results = []
    touched_imports = set()
    for sid in staged_ids:
        try:
            with db.session.begin_nested():
                ledger_row = approve_one(actor_id, sid, confirm_duplicates)
            results.append({"id": sid, "ok": True, "transaction_id": ledger_row.id})
            touched_imports.add(ledger_row.import_id)
        except AppError as exc:
            results.append({"id": sid, "ok": False, "error": exc.message})
        except IntegrityError:
            results.append({"id": sid, "ok": False, "error": "Already approved"})
    for import_id in touched_imports:
        refresh_import_status(import_id)
    db.session.commit()
    return results
