"""Account management. Every account belongs to a household the actor must be a member of."""

from sqlalchemy.exc import IntegrityError

from app.constants import ACCOUNT_STATUSES, ACCOUNT_TYPES, CURRENCY
from app.errors import Conflict, InvalidRequest, NotFound
from app.extensions import db
from app.households.service import clean_name, require_member
from app.models import Account


def _check_choice(value, allowed, label):
    if value not in allowed:
        raise InvalidRequest("%s must be one of: %s" % (label, ", ".join(allowed)))
    return value


def create_account(actor_id, household_id, account_name, account_type, institution_name="", currency=CURRENCY):
    require_member(actor_id, household_id, write=True)
    if currency != CURRENCY:
        raise InvalidRequest("Only INR accounts are supported")
    account = Account(
        household_id=household_id,
        account_name=clean_name(account_name),
        account_type=_check_choice(account_type, ACCOUNT_TYPES, "Account type"),
        institution_name=(institution_name or "").strip()[:120],
        currency=CURRENCY,
    )
    db.session.add(account)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Conflict("An account with this name already exists in the household")
    return account


def list_accounts(actor_id, household_id):
    require_member(actor_id, household_id)
    return Account.query.filter_by(household_id=household_id).order_by(Account.created_at).all()


def get_account(actor_id, account_id, write=False):
    """Load an account by id, authorizing through the account's own household."""
    account = db.session.get(Account, account_id) if account_id else None
    if account is None:
        raise NotFound("Account not found")
    try:
        require_member(actor_id, account.household_id, write=write)
    except NotFound:
        raise NotFound("Account not found")
    return account


def update_account(actor_id, account_id, account_name=None, account_type=None,
                   institution_name=None, account_status=None):
    account = get_account(actor_id, account_id, write=True)
    if account_name is not None:
        account.account_name = clean_name(account_name)
    if account_type is not None:
        account.account_type = _check_choice(account_type, ACCOUNT_TYPES, "Account type")
    if institution_name is not None:
        account.institution_name = institution_name.strip()[:120]
    if account_status is not None:
        account.account_status = _check_choice(account_status, ACCOUNT_STATUSES, "Account status")
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Conflict("An account with this name already exists in the household")
    return account
