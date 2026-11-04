"""JSON API under /api/v1. Same services and same authorization as the pages."""

from flask import Blueprint, jsonify, request

from app.api import serializers as ser
from app.auth import service as auth
from app.errors import InvalidRequest
from app.households import accounts as account_service
from app.households import service as household_service
from app.imports import review
from app.imports import service as import_service
from app.integrations import finance
from app.ledger import service as ledger
from app.session import login_user, logout_user, require_context, require_user, csrf_token

api = Blueprint("api", __name__)


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise InvalidRequest("Send a JSON object")
    return data


@api.get("/csrf")
def get_csrf():
    """API clients call this first to get a token (and a session cookie) for register/login."""
    return jsonify({"csrf_token": csrf_token()})


@api.post("/auth/register")
def register():
    data = body()
    user = auth.register(data.get("email"), data.get("display_name"), data.get("password"))
    login_user(user)
    return jsonify({"user": ser.user_json(user), "csrf_token": csrf_token()}), 201


@api.post("/auth/login")
def login():
    data = body()
    user = auth.authenticate(data.get("email"), data.get("password"))
    login_user(user)
    return jsonify({"user": ser.user_json(user), "csrf_token": csrf_token()})


@api.post("/auth/logout")
def logout():
    logout_user()
    return jsonify({"ok": True})


@api.get("/me")
def me():
    return jsonify({"user": ser.user_json(require_user(allow_unverified=True))})


@api.patch("/me")
def update_me():
    user = require_user()
    return jsonify({"user": ser.user_json(auth.update_profile(user, body().get("display_name")))})


@api.get("/households")
def households():
    user = require_user()
    return jsonify({"households": [ser.household_json(h, r) for h, r in household_service.list_households(user.id)]})


@api.post("/households")
def create_household():
    user = require_user()
    h = household_service.create_household(user.id, body().get("name"))
    return jsonify({"household": ser.household_json(h, "owner")}), 201


@api.get("/households/<household_id>")
def household(household_id):
    user = require_user()
    h, role = household_service.get_household(user.id, household_id)
    return jsonify({"household": ser.household_json(h, role),
                    "members": household_service.list_members(user.id, household_id)})


@api.get("/households/<household_id>/accounts")
def list_accounts(household_id):
    user = require_user()
    return jsonify({"accounts": [ser.account_json(a) for a in account_service.list_accounts(user.id, household_id)]})


@api.post("/households/<household_id>/accounts")
def create_account(household_id):
    user = require_user()
    d = body()
    a = account_service.create_account(user.id, household_id, d.get("account_name"), d.get("account_type"),
                                       d.get("institution_name", ""), d.get("currency", "INR"))
    return jsonify({"account": ser.account_json(a)}), 201


@api.patch("/accounts/<account_id>")
def update_account(account_id):
    user = require_user()
    d = body()
    a = account_service.update_account(user.id, account_id, d.get("account_name"), d.get("account_type"),
                                       d.get("institution_name"), d.get("account_status"))
    return jsonify({"account": ser.account_json(a)})


@api.post("/accounts/<account_id>/imports")
def upload(account_id):
    user = require_user()
    upload_file = request.files.get("file")
    if upload_file is None:
        raise InvalidRequest("Attach a file in the 'file' field")
    imp, already = import_service.create_import(user.id, account_id, upload_file.filename, upload_file.read(),
                                                request.form.get("layout", "signed_amount"))
    return jsonify({"import": ser.import_json(imp, import_service.import_stats(imp)),
                    "already_imported": already}), 200 if already else 201


@api.get("/households/<household_id>/imports")
def list_imports(household_id):
    user = require_user()
    return jsonify({"imports": [ser.import_json(i) for i in import_service.list_imports(user.id, household_id)]})


@api.get("/imports/<import_id>")
def get_import(import_id):
    user = require_user()
    imp = import_service.get_import(user.id, import_id)
    return jsonify({"import": ser.import_json(imp, import_service.import_stats(imp))})


@api.get("/imports/<import_id>/rows")
def import_rows(import_id):
    user = require_user()
    rows = import_service.list_staged(user.id, import_id, request.args.get("status") or None)
    return jsonify({"rows": [ser.staged_json(r, import_service.display_status(r)) for r in rows]})


@api.patch("/staged/<staged_id>")
def edit_row(staged_id):
    user = require_user()
    row = review.edit_staged(user.id, staged_id, {k: str(v) if v is not None else "" for k, v in body().items()})
    return jsonify({"row": ser.staged_json(row, import_service.display_status(row))})


@api.post("/staged/<staged_id>/reject")
def reject_row(staged_id):
    user = require_user()
    row = review.reject_staged(user.id, staged_id)
    return jsonify({"row": ser.staged_json(row, import_service.display_status(row))})


@api.post("/staged/<staged_id>/reopen")
def reopen_row(staged_id):
    user = require_user()
    row = review.reopen_staged(user.id, staged_id)
    return jsonify({"row": ser.staged_json(row, import_service.display_status(row))})


@api.post("/staged/approve")
def approve_rows():
    user = require_user()
    d = body()
    ids = d.get("ids")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise InvalidRequest("ids must be a list of row ids")
    return jsonify({"results": review.approve_staged(user.id, ids, bool(d.get("confirm_duplicates")))})


@api.get("/households/<household_id>/transactions")
def transactions(household_id):
    user = require_user()
    rows, total = ledger.list_transactions(
        user.id, household_id, month=request.args.get("month"), account_id=request.args.get("account_id"),
        transaction_type=request.args.get("type"), category=request.args.get("category"),
        limit=request.args.get("limit", 200, type=int), offset=request.args.get("offset", 0, type=int))
    return jsonify({"total": total, "transactions": [ser.transaction_json(t) for t in rows]})


@api.get("/transactions/<transaction_id>")
def transaction(transaction_id):
    user = require_user()
    return jsonify({"transaction": ser.transaction_json(ledger.get_transaction(user.id, transaction_id))})


@api.patch("/transactions/<transaction_id>")
def correct(transaction_id):
    user = require_user()
    t = ledger.correct_transaction(user.id, transaction_id, body())
    return jsonify({"transaction": ser.transaction_json(t)})


@api.get("/households/<household_id>/summary")
def summary(household_id):
    ctx = require_context()
    return jsonify(finance.get_monthly_summary(ctx, household_id, request.args.get("month", "")))
