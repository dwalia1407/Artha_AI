"""
Authentication service (built-in "local" provider).

This is the integration boundary for an external provider. User.auth_provider
and User.auth_ref identify the account at the provider; password hashes live
in a separate table that an external provider would not use.
"""

import re
from datetime import datetime, timezone

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth import mailer
from app.errors import Conflict, InvalidRequest, Unauthenticated
from app.extensions import db
from app.models import LocalCredential, User, new_id

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 10
VERIFY_SALT = "email-verify"
# Used so a missing user costs the same time as a wrong password.
DUMMY_HASH = generate_password_hash("not-a-real-password")


def normalize_email(email):
    return (email or "").strip().lower()


def validate_display_name(name):
    name = (name or "").strip()
    if not name or len(name) > 120:
        raise InvalidRequest("Display name is required (max 120 characters)")
    return name


def register(email, display_name, password):
    email = normalize_email(email)
    if not EMAIL_RE.match(email) or len(email) > 320:
        raise InvalidRequest("Enter a valid email address")
    display_name = validate_display_name(display_name)
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise InvalidRequest("Password must be at least %d characters" % MIN_PASSWORD_LENGTH)
    if User.query.filter_by(email=email).first():
        raise Conflict("An account with this email already exists")

    user_id = new_id()
    user = User(id=user_id, email=email, display_name=display_name,
                auth_provider="local", auth_ref=user_id)
    db.session.add(user)
    db.session.flush()  # the credential row has a foreign key to the user
    db.session.add(LocalCredential(user_id=user_id, password_hash=generate_password_hash(password)))
    db.session.commit()
    send_verification(user)
    return user


def authenticate(email, password):
    user = User.query.filter_by(email=normalize_email(email)).first()
    cred = db.session.get(LocalCredential, user.id) if user else None
    hash_to_check = cred.password_hash if cred else DUMMY_HASH
    ok = check_password_hash(hash_to_check, password or "")
    if not (user and cred and ok):
        raise Unauthenticated("Invalid email or password")
    return user


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=VERIFY_SALT)


def make_verification_token(user):
    return _serializer().dumps({"uid": user.id, "email": user.email})


def send_verification(user):
    """Returns True if an email was sent. Never raises for delivery problems."""
    token = make_verification_token(user)
    link = current_app.config["APP_BASE_URL"].rstrip("/") + "/verify/" + token
    if not mailer.is_configured():
        current_app.logger.warning("Verification email not sent for user %s: SMTP not configured", user.id)
        if current_app.config["APP_ENV"] == "development":
            # Development only: lets a developer open the real signed link by hand.
            current_app.logger.warning("DEV verification link for %s: %s", user.id, link)
        return False
    try:
        mailer.send_email(user.email, "Verify your Artha AI email",
                          "Open this link to verify your email:\n\n" + link + "\n\nIt expires in 24 hours.")
        return True
    except Exception:
        current_app.logger.warning("Verification email failed for user %s", user.id)
        return False


def verify_email(token):
    max_age = current_app.config["VERIFY_TOKEN_MAX_AGE_SECONDS"]
    try:
        data = _serializer().loads(token, max_age=max_age)
    except SignatureExpired:
        raise InvalidRequest("This verification link has expired. Request a new one.")
    except BadSignature:
        raise InvalidRequest("This verification link is not valid.")
    user = db.session.get(User, data.get("uid"))
    if user is None or user.email != data.get("email"):
        raise InvalidRequest("This verification link is not valid.")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        db.session.commit()
    return user


def update_profile(user, display_name):
    user.display_name = validate_display_name(display_name)
    db.session.commit()
    return user
