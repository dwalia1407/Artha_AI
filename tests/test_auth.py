import re

from itsdangerous import URLSafeTimedSerializer

from app import create_app
from app.auth import service as auth
from app.extensions import db
from app.models import User
from tests.conftest import Api


def test_register_login_logout(app):
    a = Api(app, "x@example.com", "Xena")
    assert a.get("/me").get_json()["user"]["email"] == "x@example.com"
    assert a.post("/auth/logout").status_code == 200
    assert a.get("/me").status_code == 401
    c = app.test_client()
    r = c.post("/api/v1/auth/login", json={"email": "X@Example.com", "password": "correct-horse-1"})
    assert r.status_code == 200
    assert c.get("/api/v1/me").status_code == 200


def test_invalid_login_and_registration(app):
    Api(app, "x@example.com", "Xena")
    c = app.test_client()
    assert c.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong-password"}).status_code == 401
    assert c.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever-long"}).status_code == 401
    assert c.post("/api/v1/auth/register", json={"email": "x@example.com", "display_name": "Dup", "password": "correct-horse-1"}).status_code == 409
    assert c.post("/api/v1/auth/register", json={"email": "bad", "display_name": "N", "password": "correct-horse-1"}).status_code == 400
    assert c.post("/api/v1/auth/register", json={"email": "y@example.com", "display_name": "N", "password": "short"}).status_code == 400
    assert c.post("/api/v1/auth/login", data="not json", content_type="text/plain").status_code == 400


def test_protected_endpoints_reject_anonymous(client):
    for method, url in [("get", "/api/v1/me"), ("get", "/api/v1/households"), ("post", "/api/v1/households"),
                        ("get", "/api/v1/households/x/accounts"), ("get", "/api/v1/imports/x"),
                        ("get", "/api/v1/transactions/x"), ("get", "/api/v1/households/x/summary?month=2026-11")]:
        assert getattr(client, method)(url).status_code == 401, url
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_profile_edit_persists_across_sessions(app):
    a = Api(app, "p@example.com", "Old Name")
    assert a.patch("/me", {"display_name": "  "}).status_code == 400
    assert a.patch("/me", {"display_name": "New Name"}).status_code == 200
    a.post("/auth/logout")
    c = app.test_client()
    c.post("/api/v1/auth/login", json={"email": "p@example.com", "password": "correct-horse-1"})
    assert c.get("/api/v1/me").get_json()["user"]["display_name"] == "New Name"


def test_password_is_hashed_not_stored(app):
    Api(app, "h@example.com", "H")
    with app.app_context():
        from app.models import LocalCredential
        cred = LocalCredential.query.first()
        assert "correct-horse-1" not in cred.password_hash


def token_for(app, email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        return auth.make_verification_token(user)


def test_email_verification_valid_expired_and_tampered(app):
    Api(app, "v@example.com", "V")
    token = token_for(app, "v@example.com")
    c = app.test_client()
    assert c.get("/verify/" + token + "x").status_code == 400
    with app.app_context():
        assert User.query.filter_by(email="v@example.com").first().email_verified_at is None
    assert c.get("/verify/" + token).status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="v@example.com").first().email_verified_at is not None

    # An expired token fails safely.
    app.config["VERIFY_TOKEN_MAX_AGE_SECONDS"] = -1
    Api(app, "w@example.com", "W")
    assert c.get("/verify/" + token_for(app, "w@example.com")).status_code == 400
    with app.app_context():
        assert User.query.filter_by(email="w@example.com").first().email_verified_at is None


def test_token_for_other_email_or_user_is_rejected(app):
    Api(app, "v@example.com", "V")
    forged = URLSafeTimedSerializer("not-the-secret", salt="email-verify").dumps({"uid": "x", "email": "v@example.com"})
    assert app.test_client().get("/verify/" + forged).status_code == 400


def test_verification_required_blocks_protected_actions(app):
    app.config["REQUIRE_EMAIL_VERIFICATION"] = True
    a = Api(app, "u@example.com", "U")
    assert a.post("/households", {"name": "Home"}).status_code == 403
    assert a.get("/me").status_code == 200
    app.test_client().get("/verify/" + token_for(app, "u@example.com"))
    assert a.post("/households", {"name": "Home"}).status_code == 201


def test_registration_survives_email_delivery_failure(app, monkeypatch):
    from app.auth import mailer
    app.config.update(SMTP_HOST="smtp.invalid", SMTP_FROM="x@example.com")
    monkeypatch.setattr(mailer.smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    a = Api(app, "m@example.com", "M")
    assert a.get("/me").get_json()["user"]["email_verified"] is False


def test_csrf_enforced_when_enabled(db_url):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_url, "SECRET_KEY": "s", "CSRF_ENABLED": True})
    with app.app_context():
        db.drop_all(); db.create_all()
    c = app.test_client()
    assert c.post("/login", data={"email": "a@b.co", "password": "x"}).status_code == 400
    page = c.get("/login").get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    assert c.post("/login", data={"email": "a@b.co", "password": "x", "csrf_token": token}).status_code == 401
    with app.app_context():
        db.drop_all()


def test_health_and_headers(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in client.get("/login").headers["Content-Security-Policy"]
