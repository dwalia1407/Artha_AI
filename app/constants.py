"""Shared constants: currency, roles, statuses, transaction types, categories."""

CURRENCY = "INR"
TIMEZONE = "Asia/Kolkata"

ROLE_OWNER = "owner"
ROLE_VIEWER = "viewer"
ROLES = (ROLE_OWNER, ROLE_VIEWER)

MEMBERSHIP_ACTIVE = "active"
MEMBERSHIP_INVITED = "invited"
MEMBERSHIP_REMOVED = "removed"
MEMBERSHIP_STATUSES = (MEMBERSHIP_ACTIVE, MEMBERSHIP_INVITED, MEMBERSHIP_REMOVED)

ACCOUNT_TYPES = ("savings", "current", "credit_card", "wallet", "other")
ACCOUNT_STATUSES = ("active", "closed")

DIRECTION_CREDIT = "credit"
DIRECTION_DEBIT = "debit"
DIRECTIONS = (DIRECTION_CREDIT, DIRECTION_DEBIT)

# Transaction type is separate from spending category.
# Meanings follow docs/contracts.md (Disha's approved finance rules).
TRANSACTION_TYPES = (
    "income",
    "purchase",
    "fee",
    "refund",
    "internal_transfer",
    "card_settlement",
    "cash_withdrawal",
    "investment",
    "loan_payment",
)

# Rows with no type or an unclear type stay pending; only these reach the ledger.
# Sanity rules: some types can only move money one way.
CREDIT_ONLY_TYPES = ("income", "refund")
DEBIT_ONLY_TYPES = ("purchase", "fee", "loan_payment", "cash_withdrawal")

# Same 13 labels as ml/contracts/v2/label_map.json (a test keeps them equal).
CATEGORIES = (
    "Bank Fees & Charges",
    "Eating Out",
    "Education & Children",
    "Entertainment & Subscriptions",
    "Groceries",
    "Healthcare",
    "Housing/Rent",
    "Insurance",
    "Personal Care",
    "Shopping & Clothing",
    "Transportation & Gas",
    "Travel",
    "Utilities",
)

VALIDATION_VALID = "valid"
VALIDATION_INVALID = "invalid"

APPROVAL_PENDING = "pending"
APPROVAL_APPROVED = "approved"
APPROVAL_REJECTED = "rejected"
APPROVAL_STATUSES = (APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED)

IMPORT_STAGED = "staged"
IMPORT_COMPLETED = "completed"
IMPORT_FAILED = "failed"
IMPORT_STATUSES = (IMPORT_STAGED, IMPORT_COMPLETED, IMPORT_FAILED)

PARSER_VERSION = "csv-v1"
