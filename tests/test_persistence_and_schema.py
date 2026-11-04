import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from app import create_app, format_inr
from app.constants import CATEGORIES
from app.extensions import db
from app.models import Transaction
from tests.conftest import Api, csv_text


def test_data_survives_restart_logout_and_new_session(app, db_url):
    a = Api(app, "r@example.com", "Rita")
    hid = a.household("Persistent")
    acc = a.account(hid)
    imp = a.upload(acc, csv_text(["2026-11-01,Pay,100.00,credit,income,"])).get_json()["import"]["id"]
    a.post("/staged/approve", {"ids": [a.rows(imp)[0]["id"]]})
    a.post("/auth/logout")

    with app.app_context():
        db.session.remove()
        db.engine.dispose()

    restarted = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": db_url, "CSRF_ENABLED": False, "SECRET_KEY": "test-secret"})
    c = restarted.test_client()
    assert c.get("/api/v1/me").status_code == 401
    assert c.post("/api/v1/auth/login", json={"email": "r@example.com", "password": "correct-horse-1"}).status_code == 200
    assert c.get("/api/v1/households").get_json()["households"][0]["name"] == "Persistent"
    txns = c.get("/api/v1/households/%s/transactions" % hid).get_json()
    assert txns["total"] == 1 and txns["transactions"][0]["amount_minor"] == 10000
    assert c.get("/api/v1/imports/" + imp).get_json()["import"]["stats"]["approved"] == 1


def test_categories_match_ml_label_map():
    labels = json.loads(Path("ml/contracts/v2/label_map.json").read_text())
    assert set(CATEGORIES) == set(labels)


def test_money_formatting_is_integer_exact():
    assert format_inr(12345650) == "\u20b91,23,456.50"
    assert format_inr(5) == "\u20b90.05" and format_inr(0) == "\u20b90.00"
    assert format_inr(-100000) == "-\u20b91,000.00" and format_inr(10000000) == "\u20b91,00,000.00"
    assert format_inr(None) == ""


def test_money_columns_are_integers(app):
    from sqlalchemy import BigInteger
    assert isinstance(Transaction.__table__.c.amount_minor.type, BigInteger)


def test_migrations_match_models(tmp_path):
    """Run Alembic on a fresh database and check no model drift remains."""
    url = os.environ.get("TEST_DATABASE_URL") or "sqlite:///" + str(tmp_path / "mig.sqlite3")
    env = dict(os.environ, DATABASE_URL=url)
    if url.startswith("postgresql"):
        from sqlalchemy import create_engine, text
        from app.config import normalize_database_url
        engine = create_engine(normalize_database_url(url))
        with engine.begin() as conn:
            conn.execute(text("drop schema public cascade; create schema public;"))
    done = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    script = ("from alembic.migration import MigrationContext\n"
              "from alembic.autogenerate import compare_metadata\n"
              "from sqlalchemy import create_engine\n"
              "from app.config import normalize_database_url\n"
              "import app.models\n"
              "from app.extensions import db\n"
              "import os\n"
              "e = create_engine(normalize_database_url(os.environ['DATABASE_URL']))\n"
              "with e.connect() as c:\n"
              "    diff = compare_metadata(MigrationContext.configure(c), db.metadata)\n"
              "print(len(diff)); print(diff)\n")
    out = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert out.stdout.splitlines()[0] == "0", out.stdout + out.stderr
