"""
Application configuration, read from environment variables.

No secrets live in the repository. See .env.example for variable names.
"""

import os

DEV_SECRET = "dev-only-secret-change-me"


def normalize_database_url(url):
    """Hosting providers often give postgres://. Pin the psycopg2 driver we install."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


def env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development")
    SECRET_KEY = os.environ.get("SECRET_KEY") or DEV_SECRET
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.environ.get("DATABASE_URL", "sqlite:///artha_dev.sqlite3")
    )
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    REQUIRE_EMAIL_VERIFICATION = env_bool("REQUIRE_EMAIL_VERIFICATION", False)
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 2 * 1024 * 1024))
    MAX_IMPORT_ROWS = int(os.environ.get("MAX_IMPORT_ROWS", 5000))
    VERIFY_TOKEN_MAX_AGE_SECONDS = 24 * 3600
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")
    TESTING = False

    @classmethod
    def validate(cls):
        """Refuse to run in production with unsafe settings."""
        if cls.APP_ENV == "production":
            if cls.SECRET_KEY == DEV_SECRET:
                raise RuntimeError("SECRET_KEY must be set in production")
            if cls.SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
                raise RuntimeError("DATABASE_URL must be PostgreSQL in production")
