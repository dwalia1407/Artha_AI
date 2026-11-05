"""Artha AI web application factory."""

import hmac
import logging
import os

from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from sqlalchemy import text
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from app.config import Config, normalize_database_url, validate_config
from app.errors import AppError, EmailNotVerified, Unauthenticated
from app.extensions import db
from app.session import csrf_token, current_user, session_lifetime


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["CSRF_ENABLED"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = session_lifetime()
    if overrides:
        app.config.update(overrides)
    app.config["SQLALCHEMY_DATABASE_URI"] = normalize_database_url(app.config["SQLALCHEMY_DATABASE_URI"])
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_UPLOAD_BYTES"] + 64 * 1024
    if not app.config.get("STORAGE_PATH"):
        app.config["STORAGE_PATH"] = os.path.join(app.instance_path, "secure_storage")
    try:
        os.makedirs(app.config["STORAGE_PATH"], exist_ok=True)
    except OSError:
        pass

    validate_config(app.config)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    db.init_app(app)

    from app.api.routes import api
    from app.web.routes import web
    app.register_blueprint(web)
    app.register_blueprint(api, url_prefix="/api/v1")

    register_hooks(app)
    register_errors(app)
    return app


def register_hooks(app):
    @app.before_request
    def enforce_https():
        if app.config.get("APP_ENV") == "production":
            proto = request.headers.get("X-Forwarded-Proto", request.scheme)
            if proto == "http":
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)
        return None

    @app.before_request
    def check_csrf():
        if not app.config["CSRF_ENABLED"] or request.method in ("GET", "HEAD", "OPTIONS"):
            return None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return None
        from flask import session
        sent = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
        expected = session.get("csrf", "")
        if not expected or not hmac.compare_digest(sent, expected):
            return error_response(AppError("Invalid or missing CSRF token"), 400, "csrf_failed")
        return None

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
            "form-action 'self'; frame-ancestors 'none'")
        if app.config.get("APP_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        if request.path != "/healthz" and not request.path.startswith("/static"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.context_processor
    def template_globals():
        from app.constants import ACCOUNT_TYPES, CATEGORIES, TRANSACTION_TYPES
        return {"csrf_token": csrf_token, "me": current_user(),
                "account_types": ACCOUNT_TYPES, "categories": CATEGORIES,
                "transaction_types": TRANSACTION_TYPES, "money": format_inr}

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("select 1"))
        except Exception:
            app.logger.error("Health check failed: database unreachable")
            return jsonify({"status": "unavailable"}), 503
        return jsonify({"status": "ok"})


def format_inr(amount_minor):
    """Format integer paise as Indian-grouped rupees, e.g. 12345650 -> 1,23,456.50. Integer maths only."""
    if amount_minor is None:
        return ""
    sign = "-" if amount_minor < 0 else ""
    rupees, paise = divmod(abs(int(amount_minor)), 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return "%s\u20b9%s.%02d" % (sign, digits, paise)


def wants_json():
    return request.path.startswith("/api/")


def error_response(exc, status, code):
    retry_after = getattr(exc, "retry_after", None)
    if wants_json():
        body = jsonify({"error": {"code": code, "message": exc.message if isinstance(exc, AppError) else str(exc),
                                  "details": getattr(exc, "details", {})}})
        if retry_after is not None:
            body.headers["Retry-After"] = str(int(retry_after))
        return body, status
    from flask import make_response
    content = render_template("error.html", status=status, message=getattr(exc, "message", str(exc)))
    r = make_response(content, status)
    if retry_after is not None:
        r.headers["Retry-After"] = str(int(retry_after))
    return r


def register_errors(app):
    @app.errorhandler(AppError)
    def handle_app_error(exc):
        db.session.rollback()
        if not wants_json():
            if isinstance(exc, EmailNotVerified):
                return redirect(url_for("web.verify_needed"))
            if isinstance(exc, Unauthenticated):
                flash("Please sign in to continue.", "error")
                return redirect(url_for("web.login"))
        return error_response(exc, exc.status, exc.code)

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(exc):
        return error_response(AppError("Upload is too large"), 413, "file_too_large")

    @app.errorhandler(HTTPException)
    def handle_http(exc):
        return error_response(AppError(exc.description or exc.name), exc.code, "http_error")

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        db.session.rollback()
        # Log the type and route only. Messages can contain row data.
        app.logger.error("Unhandled %s on %s %s", type(exc).__name__, request.method, request.path)
        return error_response(AppError("Something went wrong on our side"), 500, "internal_error")
