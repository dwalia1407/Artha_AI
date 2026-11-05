"""
Email delivery for verification messages.

Real delivery needs SMTP settings (see .env.example). Without them nothing is
sent and the caller is told so. Nothing here marks an email as verified;
verification only happens when the user opens the signed link.
"""

from email.message import EmailMessage
import smtplib
import ssl

from flask import current_app

from app.errors import ServiceUnavailable


def is_configured():
    cfg = current_app.config
    return bool(cfg.get("SMTP_HOST") and cfg.get("SMTP_FROM"))


def send_email(to_address, subject, body):
    cfg = current_app.config
    if not is_configured():
        raise ServiceUnavailable("Email delivery is not configured")
    msg = EmailMessage()
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    host = cfg["SMTP_HOST"]
    port = int(cfg.get("SMTP_PORT", 587))
    user = cfg.get("SMTP_USER", "")
    password = cfg.get("SMTP_PASSWORD", "")
    use_ssl = bool(cfg.get("SMTP_USE_SSL", False))
    use_tls = bool(cfg.get("SMTP_USE_TLS", True))

    context = ssl.create_default_context()

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as smtp:
                if use_tls:
                    smtp.starttls(context=context)
                if user:
                    smtp.login(user, password)
                smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise ServiceUnavailable("Email delivery failed") from exc
