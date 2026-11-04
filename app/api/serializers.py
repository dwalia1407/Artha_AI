"""Plain-dict versions of models for JSON responses."""


def iso(value):
    return value.isoformat() if value else None


def user_json(u):
    return {"id": u.id, "email": u.email, "display_name": u.display_name,
            "email_verified": u.email_verified_at is not None}


def household_json(h, role=None):
    return {"id": h.id, "name": h.name, "owner_id": h.owner_id, "role": role}


def account_json(a):
    return {"id": a.id, "household_id": a.household_id, "account_name": a.account_name,
            "account_type": a.account_type, "institution_name": a.institution_name,
            "currency": a.currency, "account_status": a.account_status}


def import_json(i, stats=None):
    out = {"id": i.id, "household_id": i.household_id, "account_id": i.account_id, "filename": i.filename,
           "file_hash": i.file_hash, "parser_version": i.parser_version, "import_status": i.import_status,
           "total_rows": i.total_rows, "valid_rows": i.valid_rows, "invalid_rows": i.invalid_rows,
           "error_message": i.error_message, "uploaded_at": iso(i.uploaded_at)}
    if stats is not None:
        out["stats"] = stats
    return out


def staged_json(s, status):
    return {"id": s.id, "import_id": s.import_id, "source_row_number": s.source_row_number,
            "status": status, "original_description": s.original_description, "description": s.description,
            "transaction_date": iso(s.transaction_date), "amount_minor": s.amount_minor, "currency": s.currency,
            "direction": s.direction, "transaction_type": s.transaction_type, "category": s.category,
            "suggested_category": s.suggested_category, "validation_errors": s.validation_errors,
            "potential_duplicate": s.potential_duplicate, "duplicate_candidates": s.duplicate_candidates,
            "transaction_id": s.transaction_id}


def transaction_json(t):
    return {"id": t.id, "household_id": t.household_id, "account_id": t.account_id, "import_id": t.import_id,
            "source_row_number": t.source_row_number, "amount_minor": t.amount_minor, "currency": t.currency,
            "direction": t.direction, "transaction_date": iso(t.transaction_date),
            "original_description": t.original_description, "description": t.description,
            "transaction_type": t.transaction_type, "category": t.category,
            "matched_transaction_id": t.matched_transaction_id, "approval_status": t.approval_status,
            "correction_metadata": t.correction_metadata}
