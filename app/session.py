"""Session helpers. The session cookie is signed; only the user id is stored in it."""

from datetime import timedelta
import secrets

from flask import current_app, g, has_request_context, request, session

from app.auth.context import AuthContext
from app.errors import EmailNotVerified, Unauthenticated
from app.extensions import db
from app.models import User


def login_user(user):
    session.clear()
    session["uid"] = user.id
    session["csrf"] = secrets.token_urlsafe(32)
    session.permanent = True


def logout_user():
    session.clear()


def current_user():
    if "user" not in g:
        user = None
        # Check Bearer token if present
        if has_request_context():
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                if token:
                    try:
                        from app.auth.service import authenticate_supabase_token
                        user = authenticate_supabase_token(token)
                    except Exception:
                        user = None

        if user is None:
            uid = session.get("uid")
            user = db.session.get(User, uid) if uid else None

        g.user = user
    return g.user


def require_user(allow_unverified=False):
    user = current_user()
    if user is None:
        raise Unauthenticated("Please sign in")
    if (current_app.config["REQUIRE_EMAIL_VERIFICATION"] and user.email_verified_at is None
            and not allow_unverified):
        raise EmailNotVerified("Verify your email address to continue")
    return user


def require_context():
    """Build the trusted AuthContext from the verified session or token."""
    user = require_user()
    source = "token" if has_request_context() and request.headers.get("Authorization", "").startswith("Bearer ") else "session"
    return AuthContext(user_id=user.id, email_verified=user.email_verified_at is not None, source=source)


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def session_lifetime():
    return timedelta(days=14)
