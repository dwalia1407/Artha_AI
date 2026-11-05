import json
import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from sqlalchemy.exc import IntegrityError

from app.auth.supabase import sync_supabase_user
from app.errors import NotFound
from app.extensions import db
from app.imports.storage import (
    retrieve_csv_file, purge_expired_storage, get_storage_path,
)
from app.models import Import, new_id
from app.security.rate_limiter import limiter


def test_account_household_consistency_constraint(app, alice):
    """
    Test Task 7: Database constraints guarantee that an account, import, staged row,
    and transaction cannot reference mismatched household IDs.
    """
    with app.app_context():
        # Alice creates household 1 and account 1
        h1_id = alice.household("Household One")
        h2_id = alice.household("Household Two")
        acct1_id = alice.account(h1_id, "Savings 1")

        # Attempt to insert an import pointing to acct1 but belonging to h2
        bad_import = Import(
            id=new_id(),
            household_id=h2_id,  # Mismatched! acct1 belongs to h1!
            account_id=acct1_id,
            uploaded_by=alice.user["id"],
            file_hash="hash123",
            filename="test.csv",
            parser_version="csv-v1",
            import_status="staged"
        )
        db.session.add(bad_import)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_private_csv_storage_encryption_and_retention(app, alice, tmp_path):
    """
    Test Task 6: CSV files are stored encrypted at rest, require household membership
    to retrieve, and can be purged according to retention policies.
    """
    app.config["STORAGE_PATH"] = str(tmp_path / "vault")
    raw_csv = b"date,description,amount\n2026-11-01,Groceries,3000\n"

    h_id = alice.household("Encrypted Household")
    acct_id = alice.account(h_id, "Checking")
    import_res = alice.upload(acct_id, raw_csv, filename="upload.csv")
    assert import_res.status_code == 201
    import_id = import_res.get_json()["import"]["id"]

    with app.app_context():
        # 1. File exists on disk and is ENCRYPTED (raw bytes should not match)
        enc_path = get_storage_path(h_id, acct_id, import_id)
        assert os.path.exists(enc_path)
        with open(enc_path, "rb") as f:
            disk_data = f.read()
        assert disk_data != raw_csv
        assert b"Groceries" not in disk_data  # Verified ciphertext!

        # 2. Member can retrieve and decrypt
        decrypted_bytes, filename = retrieve_csv_file(alice.user["id"], import_id)
        assert decrypted_bytes == raw_csv
        assert filename == "upload.csv"

        # 3. Non-member cannot retrieve (raises NotFound / unauthorized)
        stranger_id = new_id()
        with pytest.raises(NotFound):
            retrieve_csv_file(stranger_id, import_id)

    # 4. API endpoint to download raw CSV
    res = alice.get(f"/imports/{import_id}/file")
    assert res.status_code == 200
    assert res.data == raw_csv
    assert res.headers["Content-Type"].startswith("text/csv")
    assert "no-store" in res.headers["Cache-Control"]

    # 5. Retention policy purge: age the import by 100 days
    with app.app_context():
        imp = db.session.get(Import, import_id)
        imp.uploaded_at = datetime.now(timezone.utc) - timedelta(days=100)
        db.session.commit()

        purged = purge_expired_storage(max_age_days=90)
        assert purged >= 1
        assert not os.path.exists(enc_path)


def test_login_rate_limiting(client, app):
    """
    Test Task 5: Exceeding failed login attempts triggers 429 Too Many Requests
    with Retry-After header.
    """
    limiter.clear()
    app.config["RATE_LIMIT_LOGIN_MAX_ATTEMPTS"] = 3
    app.config["RATE_LIMIT_LOGIN_WINDOW_SECONDS"] = 60

    # 3 failed login attempts
    for _ in range(3):
        res = client.post("/api/v1/auth/login", json={"email": "victim@example.com", "password": "wrong"})
        assert res.status_code == 401

    # 4th attempt is rate-limited
    res = client.post("/api/v1/auth/login", json={"email": "victim@example.com", "password": "wrong"})
    assert res.status_code == 429
    assert res.json["error"]["code"] == "rate_limited"
    assert "Retry-After" in res.headers

    limiter.clear()


def test_supabase_auth_integration(app, client):
    """
    Test Task 2: Supabase Auth integration syncs Supabase users into local User table,
    creates authenticated sessions, and grants full access to household features.
    """
    mock_sub_user = {
        "id": "supabase-uuid-12345",
        "email": "supabase_user@example.com",
        "email_confirmed_at": "2026-11-04T12:00:00Z",
        "user_metadata": {
            "display_name": "Supabase Member"
        }
    }

    with app.app_context():
        # Test user syncing
        user = sync_supabase_user(mock_sub_user)
        assert user.email == "supabase_user@example.com"
        assert user.auth_provider == "supabase"
        assert user.auth_ref == "supabase-uuid-12345"
        assert user.email_verified_at is not None

        # Verify idempotency / update
        user2 = sync_supabase_user(mock_sub_user)
        assert user2.id == user.id

    # Test API endpoint /auth/supabase/session
    with patch("app.auth.service.authenticate_supabase_token") as mock_auth_token:
        mock_auth_token.return_value = user
        res = client.post("/api/v1/auth/supabase/session", json={"access_token": "valid-supabase-jwt"})
        assert res.status_code == 200
        assert res.json["user"]["email"] == "supabase_user@example.com"
        assert "csrf_token" in res.json

    # Test Bearer token authentication on protected routes
    with patch("app.auth.service.authenticate_supabase_token") as mock_auth_token:
        mock_auth_token.return_value = user
        res = client.get("/api/v1/me", headers={"Authorization": "Bearer valid-supabase-jwt"})
        assert res.status_code == 200
        assert res.json["user"]["email"] == "supabase_user@example.com"
