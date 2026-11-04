"""
Boundary to Disha's finance service.

Contract (docs/contracts.md):
    get_monthly_summary(auth_context, household_id, month)

The real service is NOT connected yet. register_service() is where it plugs
in. Until then this gateway raises ServiceUnavailable, so the app never
shows made-up totals. This gateway checks the actor's membership itself and
returns the service result unchanged (no recalculation).

The typed errors below are the set the future read-only tool adapter needs:
Unauthenticated, Unauthorized/NotFound, InvalidRequest, MissingData,
ServiceUnavailable (see app/errors.py).
"""

from app.auth.context import AuthContext
from app.errors import InvalidRequest, ServiceUnavailable, Unauthenticated
from app.households.service import require_member
from app.ledger.service import month_bounds

_service = None


def register_service(func):
    """func must have the signature (auth_context, household_id, month) -> dict."""
    global _service
    _service = func


def clear_service():
    global _service
    _service = None


def is_connected():
    return _service is not None


def get_monthly_summary(auth_context, household_id, month):
    if not isinstance(auth_context, AuthContext) or not auth_context.user_id:
        raise Unauthenticated("A trusted authentication context is required")
    if not isinstance(household_id, str) or not household_id:
        raise InvalidRequest("household_id is required")
    month_bounds(month)
    require_member(auth_context.user_id, household_id)
    if _service is None:
        raise ServiceUnavailable("The finance service is not connected")
    return _service(auth_context, household_id, month)
