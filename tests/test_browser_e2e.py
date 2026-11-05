"""
Browser-based end-to-end testing suite.

Simulates a real user driving the web interface through a browser session:
- Managing browser cookies and session state
- Parsing and extracting HTML forms and CSRF tokens
- Submitting web forms and following redirects
- Verifying UI rendering, tables, error messages, and flash banners
"""

from bs4 import BeautifulSoup
import io
import pytest
from werkzeug.datastructures import MultiDict

from app.auth.service import make_verification_token
from app.extensions import db
from app.models import User


class BrowserClient:
    """Simulates a browser interacting with the server-rendered web UI."""

    def __init__(self, app):
        self.client = app.test_client()
        self.app = app
        self.last_response = None
        self.last_soup = None

    def get(self, url, **kwargs):
        res = self.client.get(url, follow_redirects=True, **kwargs)
        self.last_response = res
        self.last_soup = BeautifulSoup(res.get_data(as_text=True), "html.parser")
        return res, self.last_soup

    def submit_form(self, action_url, form_data, files=None):
        """Submit a form, automatically injecting the CSRF token from the current page."""
        md = MultiDict()
        for k, v in form_data.items():
            if isinstance(v, list):
                for item in v:
                    md.add(k, item)
            else:
                md.add(k, v)

        if "csrf_token" not in md and self.last_soup:
            token_input = self.last_soup.find("input", {"name": "csrf_token"})
            if token_input:
                md.add("csrf_token", token_input.get("value", ""))

        if files:
            for k, (stream, fname) in files.items():
                md.add(k, (stream, fname))
            res = self.client.post(action_url, data=md, content_type="multipart/form-data", follow_redirects=True)
        else:
            res = self.client.post(action_url, data=md, follow_redirects=True)

        self.last_response = res
        self.last_soup = BeautifulSoup(res.get_data(as_text=True), "html.parser")
        return res, self.last_soup


def test_browser_full_e2e_journey(app):
    """
    End-to-End browser user flow:
    1. Visit /register -> fill registration form -> submit
    2. Follow email verification link
    3. Visit /login -> login with credentials -> reach /dashboard
    4. Create household 'Sharma Household' from dashboard
    5. Create account 'HDFC Salary Account' in household
    6. Upload CSV statement file
    7. Review staged transactions, set types, edit a row
    8. Approve transactions and verify they appear in /ledger with INR formatting
    9. Download original raw CSV
    10. View /summary page
    11. Logout
    """
    browser = BrowserClient(app)

    # 1. Registration
    res, soup = browser.get("/register")
    assert res.status_code == 200
    assert soup.find("form") is not None

    email = "sharma@example.com"
    res, soup = browser.submit_form("/register", {
        "email": email,
        "display_name": "Rohan Sharma",
        "password": "SecurePassword123!"
    })
    assert res.status_code == 200
    assert "Account created" in res.get_data(as_text=True)

    # 2. Email verification
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        token = make_verification_token(user)

    res, soup = browser.get(f"/verify/{token}")
    assert res.status_code == 200
    assert "Email verified" in res.get_data(as_text=True)

    # 3. Visit dashboard and create household
    res, soup = browser.get("/dashboard")
    assert res.status_code == 200
    form = soup.find("form", {"action": "/households"})
    assert form is not None

    res, soup = browser.submit_form("/households", {
        "name": "Sharma Household"
    })
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Sharma Household" in html

    # Extract household ID
    with app.app_context():
        from app.models import Household
        hh = Household.query.filter_by(name="Sharma Household").first()
        assert hh is not None
        household_id = hh.id

    # 4. Create account inside household
    res, soup = browser.get(f"/households/{household_id}")
    assert res.status_code == 200
    res, soup = browser.submit_form(f"/households/{household_id}/accounts", {
        "account_name": "HDFC Salary Account",
        "account_type": "savings",
        "institution_name": "HDFC Bank",
        "currency": "INR"
    })
    assert res.status_code == 200
    assert "Account added" in res.get_data(as_text=True)

    with app.app_context():
        from app.models import Account
        acct = Account.query.filter_by(household_id=household_id, account_name="HDFC Salary Account").first()
        assert acct is not None
        account_id = acct.id

    # 5. Upload CSV bank statement
    csv_content = (
        "date,description,amount,type,category\n"
        "2026-11-01,Monthly Salary,50000,income,income\n"
        "2026-11-03,Nature Basket Groceries,-3200,purchase,groceries\n"
        "2026-11-05,Electricity Bill,-1800,purchase,utilities\n"
    ).encode("utf-8")

    res, soup = browser.get(f"/households/{household_id}/imports")
    assert res.status_code == 200

    res, soup = browser.submit_form(
        f"/accounts/{account_id}/imports",
        {"layout": "signed_amount"},
        files={"file": (io.BytesIO(csv_content), "statement_nov.csv")}
    )
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "statement_nov.csv" in html

    # 6. Review staged transactions
    with app.app_context():
        from app.models import Import, StagedTransaction
        imp = Import.query.filter_by(account_id=account_id).first()
        assert imp is not None
        import_id = imp.id
        staged_rows = StagedTransaction.query.filter_by(import_id=import_id).all()
        assert len(staged_rows) == 3

    # Check review page displays all 3 rows
    res, soup = browser.get(f"/imports/{import_id}")
    assert res.status_code == 200
    assert "Monthly Salary" in res.get_data(as_text=True)
    assert "Nature Basket Groceries" in res.get_data(as_text=True)

    # Test editing one staged row via web form
    first_row = next(
    row for row in staged_rows
    if row.original_description == "Monthly Salary"
    )
    res, soup = browser.get(f"/staged/{first_row.id}")
    assert res.status_code == 200
    res, soup = browser.submit_form(f"/staged/{first_row.id}/edit", {
        "description": "November Tech Salary",
        "transaction_date": "2026-11-01",
        "amount": "50000",
        "category": "income",
        "type": "income",
        "direction": "credit"
    })
    assert res.status_code == 200
    assert "November Tech Salary" in res.get_data(as_text=True)

    # 7. Approve rows into ledger
    staged_ids = [r.id for r in staged_rows]
    res, soup = browser.get(f"/imports/{import_id}")
    res, soup = browser.submit_form(f"/imports/{import_id}/approve", {"ids": staged_ids})
    assert res.status_code == 200

    # 8. Inspect the ledger
    res, soup = browser.get(f"/households/{household_id}/ledger")
    assert res.status_code == 200
    ledger_html = res.get_data(as_text=True)
    assert "November Tech Salary" in ledger_html
    assert "Nature Basket Groceries" in ledger_html
    # Verify Indian Rupee formatting is displayed in table
    assert "₹50,000.00" in ledger_html
    assert "₹3,200.00" in ledger_html

    # 9. Download original raw CSV
    res = browser.client.get(f"/imports/{import_id}/download")
    assert res.status_code == 200
    assert res.data == csv_content
    assert "statement_nov.csv" in res.headers.get("Content-Disposition", "")

    # 10. Summary page
    res, soup = browser.get(f"/households/{household_id}/summary?month=2026-11")
    assert res.status_code == 200
    assert "Monthly summary" in res.get_data(as_text=True)

    # 11. Sign out
    res, soup = browser.submit_form("/logout", {})
    assert res.status_code == 200
    assert "signed out" in res.get_data(as_text=True)
