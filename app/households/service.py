"""
Households and authorization.

Every household-scoped service in the app calls require_member() with the
actor id from the trusted session. A household id sent by a browser or by a
tool is only a request, never proof of access.
"""

from app.constants import MEMBERSHIP_ACTIVE, ROLE_OWNER
from app.errors import InvalidRequest, NotFound, Unauthorized
from app.extensions import db
from app.models import Household, HouseholdMembership, User


def get_membership(actor_id, household_id):
    return HouseholdMembership.query.filter_by(
        household_id=household_id, user_id=actor_id, membership_status=MEMBERSHIP_ACTIVE
    ).first()


def require_member(actor_id, household_id, write=False):
    """
    Return the actor's active membership or raise.
    Non-members get NotFound so household ids cannot be probed.
    Viewers get Unauthorized when write=True.
    """
    membership = get_membership(actor_id, household_id) if actor_id and household_id else None
    if membership is None:
        raise NotFound("Household not found")
    if write and membership.role != ROLE_OWNER:
        raise Unauthorized("Only a household owner can make changes")
    return membership


def clean_name(name):
    name = (name or "").strip()
    if not name or len(name) > 120:
        raise InvalidRequest("Name is required (max 120 characters)")
    return name


def create_household(actor_id, name):
    name = clean_name(name)
    household = Household(name=name, owner_id=actor_id)
    db.session.add(household)
    db.session.flush()
    db.session.add(HouseholdMembership(household_id=household.id, user_id=actor_id,
                                       role=ROLE_OWNER, membership_status=MEMBERSHIP_ACTIVE))
    db.session.commit()
    return household


def list_households(actor_id):
    rows = (
        db.session.query(Household, HouseholdMembership.role)
        .join(HouseholdMembership, HouseholdMembership.household_id == Household.id)
        .filter(HouseholdMembership.user_id == actor_id,
                HouseholdMembership.membership_status == MEMBERSHIP_ACTIVE)
        .order_by(Household.created_at)
        .all()
    )
    return [(h, role) for h, role in rows]


def get_household(actor_id, household_id):
    membership = require_member(actor_id, household_id)
    return db.session.get(Household, household_id), membership.role


def rename_household(actor_id, household_id, name):
    require_member(actor_id, household_id, write=True)
    household = db.session.get(Household, household_id)
    household.name = clean_name(name)
    db.session.commit()
    return household


def list_members(actor_id, household_id):
    require_member(actor_id, household_id)
    rows = (
        db.session.query(User, HouseholdMembership)
        .join(HouseholdMembership, HouseholdMembership.user_id == User.id)
        .filter(HouseholdMembership.household_id == household_id,
                HouseholdMembership.membership_status == MEMBERSHIP_ACTIVE)
        .order_by(HouseholdMembership.created_at)
        .all()
    )
    return [{"user_id": u.id, "display_name": u.display_name, "role": m.role} for u, m in rows]
