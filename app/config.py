"""
Application configuration, read from environment variables.

No secrets live in the repository. See .env.example for variable names.
"""

import os

DEV_SECRET = "dev-only-secret-change-me"


def normalize_database_url(url):
    """Hosting providers often give postgres://. Pin the psycopg2 driver we install."""
    if not url:
        return url
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

    # SMTP Configuration
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    SMTP_FROM = os.environ.get("SMTP_FROM", "")
    SMTP_USE_TLS = env_bool("SMTP_USE_TLS", True)
    SMTP_USE_SSL = env_bool("SMTP_USE_SSL", False)

    # Auth Provider ("local" or "supabase")
    AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "local")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

    # Storage & Retention
    STORAGE_PATH = os.environ.get("STORAGE_PATH", "")
    STORAGE_ENCRYPTION_KEY = os.environ.get("STORAGE_ENCRYPTION_KEY", "")
    CSV_RETENTION_DAYS = int(os.environ.get("CSV_RETENTION_DAYS", 90))

    # Rate Limiting
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS = int(os.environ.get("RATE_LIMIT_LOGIN_MAX_ATTEMPTS", 5))
    RATE_LIMIT_LOGIN_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_LOGIN_WINDOW_SECONDS", 900))
    RATE_LIMIT_REGISTER_MAX_ATTEMPTS = int(os.environ.get("RATE_LIMIT_REGISTER_MAX_ATTEMPTS", 10))
    RATE_LIMIT_REGISTER_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_REGISTER_WINDOW_SECONDS", 3600))

    TESTING = False

    @classmethod
    def validate(cls):
        """Refuse to run in production with unsafe settings."""
        validate_config(cls)


def validate_config(cfg):
    """
    Validate effective configuration for security invariants.
    Works on Config class or Flask app.config mapping.
    """
    def get_val(key, default=None):
        if isinstance(cfg, dict) or hasattr(cfg, "__getitem__"):
            try:
                return cfg[key]
            except KeyError:
                return getattr(Config, key, default)
        return getattr(cfg, key, default)

    app_env = get_val("APP_ENV", "development")
    if app_env != "production":
        return

    secret_key = get_val("SECRET_KEY", "")
    if not secret_key or secret_key == DEV_SECRET:
        raise RuntimeError("SECRET_KEY must be set to a strong secret in production")
    if len(secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")

    testing = get_val("TESTING", False)
    if not testing:
        db_uri = get_val("SQLALCHEMY_DATABASE_URI", "")
        if not db_uri or db_uri.startswith("sqlite"):
            raise RuntimeError("DATABASE_URL must be PostgreSQL in production")

    session_secure = get_val("SESSION_COOKIE_SECURE", False)
    if not session_secure:
        raise RuntimeError("SESSION_COOKIE_SECURE must be True in production")

    session_httponly = get_val("SESSION_COOKIE_HTTPONLY", True)
    if not session_httponly:
        raise RuntimeError("SESSION_COOKIE_HTTPONLY must be True in production")

    samesite = get_val("SESSION_COOKIE_SAMESITE", "Lax")
    if samesite not in ("Lax", "Strict"):
        raise RuntimeError("SESSION_COOKIE_SAMESITE must be 'Lax' or 'Strict' in production")

    app_base_url = get_val("APP_BASE_URL", "")
    if not app_base_url or not app_base_url.startswith("https://"):
        raise RuntimeError("APP_BASE_URL must use HTTPS in production (got %r)" % app_base_url)

    require_email_verif = get_val("REQUIRE_EMAIL_VERIFICATION", False)
    if not require_email_verif:
        raise RuntimeError("REQUIRE_EMAIL_VERIFICATION must be True in production")

    auth_provider = get_val("AUTH_PROVIDER", "local")
    if auth_provider == "supabase":
        supabase_url = get_val("SUPABASE_URL", "")
        supabase_key = get_val("SUPABASE_ANON_KEY", "")
        if not supabase_url or not supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set when AUTH_PROVIDER is 'supabase'")
    else:
        # Local auth provider with email verification in production requires configured SMTP
        smtp_host = get_val("SMTP_HOST", "")
        smtp_from = get_val("SMTP_FROM", "")
        if not smtp_host or not smtp_from:
            raise RuntimeError("SMTP_HOST and SMTP_FROM must be configured for email verification in production")
