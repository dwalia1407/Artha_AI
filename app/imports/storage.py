"""
Secure private CSV storage with encryption at rest and retention management.

Uploaded raw CSV files contain sensitive financial statements and must never
be stored in plain text or accessible without strict membership authorization.
"""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import os
from flask import current_app

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.errors import NotFound
from app.households.service import require_member
from app.models import Import


_FERNET_SALT = b"artha-secure-csv-storage-salt-v1"


def get_fernet_cipher():
    """Derive a stable 32-byte key from STORAGE_ENCRYPTION_KEY or SECRET_KEY."""
    raw_key = current_app.config.get("STORAGE_ENCRYPTION_KEY") or current_app.config.get("SECRET_KEY", "default-key")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_FERNET_SALT,
        iterations=100000,
    )
    derived_key = base64.urlsafe_b64encode(kdf.derive(raw_key.encode("utf-8")))
    return Fernet(derived_key)


def get_storage_path(household_id, account_id, import_id):
    base_dir = current_app.config.get("STORAGE_PATH") or os.path.join(current_app.instance_path, "secure_storage")
    folder = os.path.join(base_dir, household_id, account_id)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{import_id}.csv.enc")


def store_csv_file(household_id, account_id, import_id, raw_bytes):
    """Encrypt and store the raw CSV file on disk."""
    if not raw_bytes:
        return None
    cipher = get_fernet_cipher()
    encrypted_data = cipher.encrypt(raw_bytes)

    target_path = get_storage_path(household_id, account_id, import_id)
    with open(target_path, "wb") as f:
        f.write(encrypted_data)
    return target_path


def retrieve_csv_file(actor_id, import_id):
    """
    Authenticate membership and retrieve decrypted raw CSV bytes and filename.
    Returns (raw_bytes, filename).
    """
    imp = Import.query.filter_by(id=import_id).first()
    if not imp:
        raise NotFound("Import not found")

    require_member(actor_id, imp.household_id)

    file_path = get_storage_path(imp.household_id, imp.account_id, imp.id)
    if not os.path.exists(file_path):
        raise NotFound("Raw file is no longer available or was purged per retention policy")

    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    cipher = get_fernet_cipher()
    raw_bytes = cipher.decrypt(encrypted_data)
    return raw_bytes, imp.filename


def purge_expired_storage(max_age_days=None):
    """
    Retention policy runner: deletes encrypted CSV files older than max_age_days.
    Returns count of deleted files.
    """
    days = max_age_days if max_age_days is not None else current_app.config.get("CSV_RETENTION_DAYS", 90)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    expired_imports = Import.query.filter(Import.uploaded_at < cutoff).all()

    purged = 0
    for imp in expired_imports:
        file_path = get_storage_path(imp.household_id, imp.account_id, imp.id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                purged += 1
            except OSError:
                pass
    return purged
