"""
Supabase Auth (GoTrue) integration.

Integrates Supabase Auth as an established external authentication provider
while preserving all existing household, account, CSV import, and ledger functionality.
"""

from datetime import datetime, timezone
import json
import urllib.request
import urllib.error
from flask import current_app

from app.errors import Conflict, InvalidRequest, ServiceUnavailable, Unauthenticated
from app.extensions import db
from app.models import User, new_id


class SupabaseAuthService:
    def __init__(self, url=None, anon_key=None, service_role_key=None, jwt_secret=None):
        self._url = url
        self._anon_key = anon_key
        self._service_role_key = service_role_key
        self._jwt_secret = jwt_secret

    @property
    def url(self):
        return (self._url or current_app.config.get("SUPABASE_URL", "")).rstrip("/")

    @property
    def anon_key(self):
        return self._anon_key or current_app.config.get("SUPABASE_ANON_KEY", "")

    def is_configured(self):
        return bool(self.url and self.anon_key)

    def _request(self, endpoint, data=None, token=None, method=None):
        if not self.is_configured():
            raise ServiceUnavailable("Supabase Auth is not configured")

        full_url = f"{self.url}/auth/v1/{endpoint.lstrip('/')}"
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
            "User-Agent": "Artha-AI-Backend/1.0",
        }
        auth_token = token or self.anon_key
        headers["Authorization"] = f"Bearer {auth_token}"

        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(full_url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
                return json.loads(content.decode("utf-8")) if content else {}
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            err_json = {}
            try:
                err_json = json.loads(err_body)
            except Exception:
                pass
            msg = err_json.get("error_description") or err_json.get("msg") or err_json.get("message") or f"Supabase Auth error ({exc.code})"

            if exc.code == 400:
                if "already registered" in msg.lower() or "user already exists" in msg.lower():
                    raise Conflict("An account with this email already exists")
                raise InvalidRequest(msg)
            elif exc.code == 401 or exc.code == 403:
                raise Unauthenticated(msg)
            elif exc.code == 422:
                raise InvalidRequest(msg)
            raise ServiceUnavailable(f"Supabase Auth service returned error: {msg}")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ServiceUnavailable("Could not connect to Supabase Auth service") from exc

    def sign_up(self, email, password, display_name=""):
        payload = {
            "email": email,
            "password": password,
            "data": {"display_name": display_name}
        }
        return self._request("signup", data=payload, method="POST")

    def sign_in_with_password(self, email, password):
        payload = {
            "email": email,
            "password": password
        }
        return self._request("token?grant_type=password", data=payload, method="POST")

    def get_user_from_token(self, access_token):
        return self._request("user", token=access_token, method="GET")

    def resend_verification(self, email):
        payload = {
            "type": "signup",
            "email": email
        }
        return self._request("resend", data=payload, method="POST")


supabase_auth = SupabaseAuthService()


def parse_iso_datetime(dt_str):
    if not dt_str:
        return None
    # Support '2026-11-04T12:00:00Z' and '2026-11-04T12:00:00.123456Z'
    clean_str = dt_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(clean_str)
    except Exception:
        return None


def sync_supabase_user(supabase_user_dict):
    """
    Map/sync a Supabase authenticated user into the local database User record.
    Returns the local User object with valid foreign keys and memberships.
    """
    sub_id = supabase_user_dict.get("id")
    if not sub_id:
        raise InvalidRequest("Invalid user record returned by Supabase")

    email = (supabase_user_dict.get("email") or "").strip().lower()
    if not email:
        raise InvalidRequest("User record has no email address")

    user_meta = supabase_user_dict.get("user_metadata") or {}
    display_name = user_meta.get("display_name") or supabase_user_dict.get("display_name") or email.split("@")[0]

    confirmed_at_str = supabase_user_dict.get("email_confirmed_at") or supabase_user_dict.get("confirmed_at")
    verified_at = parse_iso_datetime(confirmed_at_str)

    user = User.query.filter_by(auth_provider="supabase", auth_ref=sub_id).first()
    if not user:
        # Check if user registered locally with same email before
        user = User.query.filter_by(email=email).first()
        if user:
            user.auth_provider = "supabase"
            user.auth_ref = sub_id
            if verified_at and not user.email_verified_at:
                user.email_verified_at = verified_at
        else:
            user = User(
                id=new_id(),
                email=email,
                display_name=display_name[:120],
                auth_provider="supabase",
                auth_ref=sub_id,
                email_verified_at=verified_at
            )
            db.session.add(user)
    else:
        # Update display name / verified timestamp if changed
        if verified_at and not user.email_verified_at:
            user.email_verified_at = verified_at
        if display_name and not user.display_name:
            user.display_name = display_name[:120]

    db.session.commit()
    return user

