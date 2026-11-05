import pytest
from app import create_app
from app.config import validate_config

STRONG_SECRET = "a" * 32
PG_URL = "postgresql://user:pass@localhost:5432/artha_prod"


def test_production_rejects_weak_or_dev_secret():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": "dev-only-secret-change-me",
            "SQLALCHEMY_DATABASE_URI": PG_URL,
            "SESSION_COOKIE_SECURE": True,
            "APP_BASE_URL": "https://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": True,
            "SMTP_HOST": "smtp.example.com",
            "SMTP_FROM": "no-reply@artha.ai"
        })

    with pytest.raises(RuntimeError, match="at least 32"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": "short-secret",
            "SQLALCHEMY_DATABASE_URI": PG_URL,
            "SESSION_COOKIE_SECURE": True,
            "APP_BASE_URL": "https://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": True,
            "SMTP_HOST": "smtp.example.com",
            "SMTP_FROM": "no-reply@artha.ai"
        })


def test_production_rejects_sqlite():
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": STRONG_SECRET,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///prod.db",
            "SESSION_COOKIE_SECURE": True,
            "APP_BASE_URL": "https://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": True,
            "SMTP_HOST": "smtp.example.com",
            "SMTP_FROM": "no-reply@artha.ai"
        })


def test_production_rejects_insecure_cookie():
    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": STRONG_SECRET,
            "SQLALCHEMY_DATABASE_URI": PG_URL,
            "SESSION_COOKIE_SECURE": False,
            "APP_BASE_URL": "https://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": True,
            "SMTP_HOST": "smtp.example.com",
            "SMTP_FROM": "no-reply@artha.ai"
        })


def test_production_rejects_http_base_url():
    with pytest.raises(RuntimeError, match="HTTPS"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": STRONG_SECRET,
            "SQLALCHEMY_DATABASE_URI": PG_URL,
            "SESSION_COOKIE_SECURE": True,
            "APP_BASE_URL": "http://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": True,
            "SMTP_HOST": "smtp.example.com",
            "SMTP_FROM": "no-reply@artha.ai"
        })


def test_production_rejects_disabled_email_verification():
    with pytest.raises(RuntimeError, match="REQUIRE_EMAIL_VERIFICATION"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": STRONG_SECRET,
            "SQLALCHEMY_DATABASE_URI": PG_URL,
            "SESSION_COOKIE_SECURE": True,
            "APP_BASE_URL": "https://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": False,
            "SMTP_HOST": "smtp.example.com",
            "SMTP_FROM": "no-reply@artha.ai"
        })


def test_production_rejects_missing_email_provider():
    with pytest.raises(RuntimeError, match="SMTP_HOST and SMTP_FROM"):
        validate_config({
            "APP_ENV": "production",
            "SECRET_KEY": STRONG_SECRET,
            "SQLALCHEMY_DATABASE_URI": PG_URL,
            "SESSION_COOKIE_SECURE": True,
            "APP_BASE_URL": "https://artha.ai",
            "REQUIRE_EMAIL_VERIFICATION": True,
            "SMTP_HOST": "",
            "SMTP_FROM": ""
        })


def test_production_valid_with_smtp():
    validate_config({
        "APP_ENV": "production",
        "SECRET_KEY": STRONG_SECRET,
        "SQLALCHEMY_DATABASE_URI": PG_URL,
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "APP_BASE_URL": "https://artha.ai",
        "REQUIRE_EMAIL_VERIFICATION": True,
        "SMTP_HOST": "smtp.example.com",
        "SMTP_FROM": "no-reply@artha.ai",
        "AUTH_PROVIDER": "local"
    })


def test_production_valid_with_supabase():
    validate_config({
        "APP_ENV": "production",
        "SECRET_KEY": STRONG_SECRET,
        "SQLALCHEMY_DATABASE_URI": PG_URL,
        "SESSION_COOKIE_SECURE": True,
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "APP_BASE_URL": "https://artha.ai",
        "REQUIRE_EMAIL_VERIFICATION": True,
        "AUTH_PROVIDER": "supabase",
        "SUPABASE_URL": "https://project.supabase.co",
        "SUPABASE_ANON_KEY": "anon-key-abc"
    })


def test_production_security_headers_and_https_redirect(db_url):
    prod_app = create_app({
        "TESTING": True,
        "APP_ENV": "production",
        "SECRET_KEY": STRONG_SECRET,
        "SQLALCHEMY_DATABASE_URI": db_url,
        "SESSION_COOKIE_SECURE": True,
        "APP_BASE_URL": "https://artha.ai",
        "REQUIRE_EMAIL_VERIFICATION": True,
        "SMTP_HOST": "smtp.example.com",
        "SMTP_FROM": "no-reply@artha.ai",
        "CSRF_ENABLED": False
    })
    client = prod_app.test_client()

    # Test HTTP -> HTTPS redirect
    res = client.get("/healthz", headers={"X-Forwarded-Proto": "http"})
    assert res.status_code == 301
    assert res.headers["Location"].startswith("https://")

    # Test HSTS header on secure request
    res = client.get("/healthz", headers={"X-Forwarded-Proto": "https"})
    assert res.status_code == 200
    assert "Strict-Transport-Security" in res.headers
    assert "max-age=31536000" in res.headers["Strict-Transport-Security"]

