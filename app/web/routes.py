"""Server-rendered pages. Every handler calls a service with the session's actor id."""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import service as auth
from app.constants import APPROVAL_PENDING
from app.errors import AppError, InvalidRequest
from app.extensions import db
from app.households import accounts as account_service
from app.households import service as household_service
from app.imports import review
from app.imports import service as import_service
from app.integrations import finance
from app.ledger import service as ledger
from app.models import Account, Household
from app.session import current_user, login_user, logout_user, require_context, require_user

web = Blueprint("web", __name__)


def role_of(user, household_id):
    return household_service.require_member(user.id, household_id).role


@web.get("/")
def index():
    if current_user():
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.login"))


@web.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            user = auth.register(request.form.get("email"), request.form.get("display_name"),
                                 request.form.get("password"))
        except AppError as exc:
            flash(exc.message, "error")
            return render_template("register.html", form=request.form), exc.status
        login_user(user)
        flash("Account created. Check your email for the verification link.", "ok")
        return redirect(url_for("web.dashboard"))
    return render_template("register.html", form={})


@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user = auth.authenticate(request.form.get("email"), request.form.get("password"))
        except AppError as exc:
            flash(exc.message, "error")
            return render_template("login.html", form=request.form), exc.status
        login_user(user)
        return redirect(url_for("web.dashboard"))
    return render_template("login.html", form={})


@web.post("/logout")
def logout():
    logout_user()
    flash("You have been signed out.", "ok")
    return redirect(url_for("web.login"))


@web.get("/verify/<token>")
def verify(token):
    try:
        auth.verify_email(token)
    except AppError as exc:
        return render_template("error.html", status=400, message=exc.message), 400
    flash("Email verified.", "ok")
    return redirect(url_for("web.dashboard") if current_user() else url_for("web.login"))


@web.get("/verify-needed")
def verify_needed():
    require_user(allow_unverified=True)
    return render_template("verify_needed.html")


@web.post("/verify/resend")
def verify_resend():
    user = require_user(allow_unverified=True)
    sent = auth.send_verification(user)
    flash("Verification email sent." if sent else "We could not send the email. Email delivery may not be set up yet.",
          "ok" if sent else "error")
    return redirect(url_for("web.verify_needed"))


@web.get("/dashboard")
def dashboard():
    user = require_user()
    return render_template("dashboard.html", households=household_service.list_households(user.id))


@web.route("/profile", methods=["GET", "POST"])
def profile():
    user = require_user()
    if request.method == "POST":
        try:
            auth.update_profile(user, request.form.get("display_name"))
            flash("Profile saved.", "ok")
        except AppError as exc:
            flash(exc.message, "error")
            return render_template("profile.html"), exc.status
        return redirect(url_for("web.profile"))
    return render_template("profile.html")


@web.post("/households")
def create_household():
    user = require_user()
    try:
        household = household_service.create_household(user.id, request.form.get("name"))
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.dashboard"))
    return redirect(url_for("web.household", household_id=household.id))


@web.get("/households/<household_id>")
def household(household_id):
    user = require_user()
    h, role = household_service.get_household(user.id, household_id)
    return render_template("household.html", household=h, role=role,
                           members=household_service.list_members(user.id, household_id),
                           accounts=account_service.list_accounts(user.id, household_id),
                           imports=import_service.list_imports(user.id, household_id)[:5])


@web.post("/households/<household_id>/rename")
def rename_household(household_id):
    user = require_user()
    try:
        household_service.rename_household(user.id, household_id, request.form.get("name"))
        flash("Household renamed.", "ok")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("web.household", household_id=household_id))


@web.post("/households/<household_id>/accounts")
def create_account(household_id):
    user = require_user()
    try:
        account_service.create_account(user.id, household_id, request.form.get("account_name"),
                                       request.form.get("account_type"), request.form.get("institution_name", ""))
        flash("Account added.", "ok")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("web.household", household_id=household_id))


@web.post("/accounts/<account_id>")
def edit_account(account_id):
    user = require_user()
    account = account_service.get_account(user.id, account_id)
    try:
        account_service.update_account(user.id, account_id, request.form.get("account_name"),
                                       request.form.get("account_type"), request.form.get("institution_name"),
                                       request.form.get("account_status"))
        flash("Account updated.", "ok")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("web.household", household_id=account.household_id))


@web.get("/households/<household_id>/imports")
def imports_page(household_id):
    user = require_user()
    h, role = household_service.get_household(user.id, household_id)
    accounts = [a for a in account_service.list_accounts(user.id, household_id) if a.account_status == "active"]
    return render_template("imports.html", household=h, role=role, accounts=accounts,
                           imports=import_service.list_imports(user.id, household_id))


@web.post("/accounts/<account_id>/imports")
def upload_import(account_id):
    user = require_user()
    account = account_service.get_account(user.id, account_id)
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        flash("Choose a CSV file to upload.", "error")
        return redirect(url_for("web.imports_page", household_id=account.household_id))
    try:
        imp, already = import_service.create_import(user.id, account_id, upload.filename, upload.read(),
                                                    request.form.get("layout", "signed_amount"))
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.imports_page", household_id=account.household_id))
    if already:
        flash("This exact file was already imported for this account. No new rows were added.", "ok")
    return redirect(url_for("web.import_review", import_id=imp.id))


@web.get("/imports/<import_id>")
def import_review(import_id):
    user = require_user()
    imp = import_service.get_import(user.id, import_id)
    status = request.args.get("status") or None
    rows = import_service.list_staged(user.id, import_id, status)
    return render_template("review.html", imp=imp, rows=rows, status=status,
                           stats=import_service.import_stats(imp),
                           role=role_of(user, imp.household_id),
                           display_status=import_service.display_status)


@web.get("/staged/<staged_id>")
def staged_detail(staged_id):
    user = require_user()
    row = review.get_staged(user.id, staged_id)
    return render_template("staged.html", row=row, role=role_of(user, row.household_id),
                           display_status=import_service.display_status)


@web.post("/staged/<staged_id>/edit")
def staged_edit(staged_id):
    user = require_user()
    changes = {k: request.form[k] for k in review.EDITABLE_FIELDS if k in request.form}
    try:
        review.edit_staged(user.id, staged_id, changes)
        flash("Row updated.", "ok")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("web.staged_detail", staged_id=staged_id))


@web.post("/staged/<staged_id>/reject")
def staged_reject(staged_id):
    user = require_user()
    try:
        row = review.reject_staged(user.id, staged_id)
        flash("Row rejected. It will not count in any totals.", "ok")
    except AppError as exc:
        flash(exc.message, "error")
        row = review.get_staged(user.id, staged_id)
    return redirect(url_for("web.import_review", import_id=row.import_id))


@web.post("/staged/<staged_id>/reopen")
def staged_reopen(staged_id):
    user = require_user()
    try:
        row = review.reopen_staged(user.id, staged_id)
    except AppError as exc:
        flash(exc.message, "error")
        row = review.get_staged(user.id, staged_id)
    return redirect(url_for("web.import_review", import_id=row.import_id))


@web.post("/imports/<import_id>/approve")
def approve(import_id):
    user = require_user()
    imp = import_service.get_import(user.id, import_id)
    ids = request.form.getlist("ids")
    if not ids:
        flash("Select at least one row.", "error")
        return redirect(url_for("web.import_review", import_id=imp.id))
    # Only ids that belong to this import are accepted from the form.
    own = {r.id for r in import_service.list_staged(user.id, imp.id)}
    ids = [i for i in ids if i in own]
    confirm = request.form.get("confirm_duplicates") == "yes"
    try:
        results = review.approve_staged(user.id, ids, confirm)
    except AppError as exc:
        flash(exc.message, "error")
        return redirect(url_for("web.import_review", import_id=imp.id))
    done = sum(1 for r in results if r["ok"])
    flash("%d row(s) approved into the ledger." % done, "ok")
    for r in results:
        if not r["ok"]:
            flash("Row not approved: " + r["error"], "error")
    return redirect(url_for("web.import_review", import_id=imp.id))


@web.post("/imports/<import_id>/set-type")
def set_type(import_id):
    user = require_user()
    imp = import_service.get_import(user.id, import_id)
    own = {r.id for r in import_service.list_staged(user.id, imp.id)}
    ids = [i for i in request.form.getlist("ids") if i in own]
    if not ids:
        flash("Select at least one row.", "error")
    else:
        results = review.set_type_for_rows(user.id, ids, request.form.get("type", ""))
        failed = [r for r in results if not r["ok"]]
        flash("Type set on %d row(s)." % (len(results) - len(failed)), "ok")
        for r in failed:
            flash("Row not changed: " + r["error"], "error")
    return redirect(url_for("web.import_review", import_id=imp.id))


@web.get("/households/<household_id>/ledger")
def ledger_page(household_id):
    user = require_user()
    h, role = household_service.get_household(user.id, household_id)
    month = request.args.get("month") or None
    try:
        rows, total = ledger.list_transactions(
            user.id, household_id, month=month, account_id=request.args.get("account_id") or None,
            transaction_type=request.args.get("type") or None, category=request.args.get("category") or None,
            offset=int(request.args.get("offset", 0) or 0))
    except (AppError, ValueError) as exc:
        flash(getattr(exc, "message", "Invalid filter"), "error")
        rows, total = [], 0
    accounts = {a.id: a for a in account_service.list_accounts(user.id, household_id)}
    return render_template("ledger.html", household=h, role=role, rows=rows, total=total,
                           accounts=accounts, filters=request.args)


@web.get("/transactions/<transaction_id>")
def transaction_detail(transaction_id):
    user = require_user()
    txn = ledger.get_transaction(user.id, transaction_id)
    return render_template("transaction.html", txn=txn, role=role_of(user, txn.household_id),
                           account=db.session.get(Account, txn.account_id))


@web.post("/transactions/<transaction_id>/correct")
def transaction_correct(transaction_id):
    user = require_user()
    changes = {k: request.form[k] for k in ("category", "transaction_type", "matched_transaction_id", "description")
               if k in request.form}
    try:
        ledger.correct_transaction(user.id, transaction_id, changes)
        flash("Correction saved. The previous values are kept in the history.", "ok")
    except AppError as exc:
        flash(exc.message, "error")
    return redirect(url_for("web.transaction_detail", transaction_id=transaction_id))


@web.get("/households/<household_id>/summary")
def summary_page(household_id):
    ctx = require_context()
    h, role = household_service.get_household(ctx.user_id, household_id)
    month = request.args.get("month") or ""
    result, problem = None, None
    if month:
        try:
            result = finance.get_monthly_summary(ctx, household_id, month)
        except AppError as exc:
            problem = exc.message
    return render_template("summary.html", household=h, role=role, month=month, result=result,
                           problem=problem, connected=finance.is_connected())
