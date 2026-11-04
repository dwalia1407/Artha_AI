"""
Email delivery for verification messages.

Real delivery needs SMTP settings (see .env.example). Without them nothing is
sent and the caller is told so. Nothing here marks an email as verified;
verification only happens when the user opens the signed link.
"""

import smtplib
from email.message import EmailMessage

from flask import current_app

from app.errors import ServiceUnavailable


def is_configured():
    cfg = current_app.config
    return bool(cfg["SMTP_HOST"] and cfg["SMTP_FROM"])


def send_email(to_address, subject, body):
    cfg = current_app.config
    if not is_configured():
        raise ServiceUnavailable("Email delivery is not configured")
    msg = EmailMessage()
    msg["From"] = cfg["SMTP_FROM"]
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as smtp:
            smtp.starttls()
            if cfg["SMTP_USER"]:
                smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise ServiceUnavailable("Email delivery failed") from exc
