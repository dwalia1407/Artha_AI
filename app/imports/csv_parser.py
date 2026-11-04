"""
CSV parsing and row validation.

Pure functions, no database access. Amounts become integer paise through
Decimal text parsing, never floats. Uploaded content is only read as data.
See docs/csv_import_specification.md for the supported format.
"""

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal

from app.constants import (
    CATEGORIES, CREDIT_ONLY_TYPES, CURRENCY, DEBIT_ONLY_TYPES, DIRECTION_CREDIT,
    DIRECTION_DEBIT, TRANSACTION_TYPES,
)

MAX_DESCRIPTION_LENGTH = 500
MAX_CELL_LENGTH = 2000
MAX_AMOUNT_MINOR = 10 ** 15

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y")

DIRECTION_WORDS = {
    "credit": DIRECTION_CREDIT, "cr": DIRECTION_CREDIT, "c": DIRECTION_CREDIT,
    "debit": DIRECTION_DEBIT, "dr": DIRECTION_DEBIT, "d": DIRECTION_DEBIT,
}

# Preset column layouts. A caller can override any header name.
PRESETS = {
    "signed_amount": {
        "required": ["date", "description", "amount"],
        "optional": ["direction", "currency", "type", "category"],
        "headers": {"date": "date", "description": "description", "amount": "amount",
                    "direction": "direction", "currency": "currency",
                    "type": "type", "category": "category"},
    },
    "debit_credit": {
        "required": ["date", "description", "debit", "credit"],
        "optional": ["currency", "type", "category"],
        "headers": {"date": "date", "description": "description", "debit": "debit",
                    "credit": "credit", "currency": "currency",
                    "type": "type", "category": "category"},
    },
}


class ImportFileError(Exception):
    """The whole file cannot be used (not a single bad row)."""


def decode_bytes(data):
    if b"\x00" in data:
        raise ImportFileError("File contains binary data and is not a text CSV")
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        raise ImportFileError("File encoding is not supported (use UTF-8)")


def parse_amount(text):
    """Return signed integer paise from text such as '1,23,456.50' or '(250.00)'."""
    if text is None:
        raise ValueError("Amount is missing")
    s = text.strip()
    if not s:
        raise ValueError("Amount is missing")
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()
    s = re.sub(r"^(inr|rs\.?|\u20b9)\s*", "", s, flags=re.IGNORECASE)
    s = s.replace(",", "").strip()
    if s.startswith("-"):
        negative = True
        s = s[1:]
    elif s.startswith("+"):
        s = s[1:]
    if not re.fullmatch(r"\d+(\.\d{1,2})?", s):
        raise ValueError("Amount '%s' is not a valid number with at most 2 decimals" % text.strip()[:40])
    paise = int((Decimal(s) * 100).to_integral_value())
    if paise == 0:
        raise ValueError("Amount must not be zero")
    if paise >= MAX_AMOUNT_MINOR:
        raise ValueError("Amount is too large")
    return -paise if negative else paise


def parse_date(text):
    s = (text or "").strip()
    if not s:
        raise ValueError("Date is missing")
    for fmt in DATE_FORMATS:
        try:
            d = datetime.strptime(s, fmt).date()
        except ValueError:
            continue
        if not (2000 <= d.year <= 2100):
            raise ValueError("Date year must be between 2000 and 2100")
        return d
    raise ValueError("Date '%s' is not valid (use YYYY-MM-DD or DD/MM/YYYY)" % s[:40])


def normalize_description(text):
    return " ".join((text or "").casefold().split())


def canonical(value, allowed):
    """Case-insensitive match against a fixed list; returns the canonical value or None."""
    key = (value or "").strip().casefold()
    for item in allowed:
        if item.casefold() == key:
            return item
    return None


def type_direction_error(transaction_type, direction):
    """Some types only make sense one way: income and refunds are credits, purchases are debits."""
    if transaction_type in CREDIT_ONLY_TYPES and direction != DIRECTION_CREDIT:
        return "A %s must be a credit" % transaction_type.replace("_", " ")
    if transaction_type in DEBIT_ONLY_TYPES and direction != DIRECTION_DEBIT:
        return "A %s must be a debit" % transaction_type.replace("_", " ")
    return None


def check_values(description, date_text, amount_minor, direction, currency, type_text, category_text):
    """
    Validate already-split fields. amount_minor is a positive int or None.
    Returns (clean dict, errors list). Used for CSV rows and for user edits.
    """
    errors = []
    clean = {"description": (description or "").strip(), "transaction_date": None,
             "amount_minor": None, "direction": None, "currency": CURRENCY,
             "transaction_type": None, "category": None}

    if not clean["description"]:
        errors.append({"field": "description", "message": "Description is empty"})
    elif len(clean["description"]) > MAX_DESCRIPTION_LENGTH:
        errors.append({"field": "description", "message": "Description is longer than %d characters" % MAX_DESCRIPTION_LENGTH})

    try:
        clean["transaction_date"] = parse_date(date_text)
    except ValueError as exc:
        errors.append({"field": "date", "message": str(exc)})

    if amount_minor is None or amount_minor <= 0:
        errors.append({"field": "amount", "message": "Amount must be a positive number"})
    else:
        clean["amount_minor"] = amount_minor

    if direction in (DIRECTION_CREDIT, DIRECTION_DEBIT):
        clean["direction"] = direction
    else:
        errors.append({"field": "direction", "message": "Direction must be credit or debit"})

    cur = (currency or "").strip().upper() or CURRENCY
    if cur != CURRENCY:
        errors.append({"field": "currency", "message": "Unsupported currency '%s' (only INR)" % cur[:10]})

    if (type_text or "").strip():
        t = canonical(type_text, TRANSACTION_TYPES)
        if t is None:
            errors.append({"field": "type", "message": "Unknown transaction type '%s'" % type_text.strip()[:40]})
        else:
            clean["transaction_type"] = t

    if clean["transaction_type"] and clean["direction"]:
        message = type_direction_error(clean["transaction_type"], clean["direction"])
        if message:
            errors.append({"field": "type", "message": message})

    if (category_text or "").strip():
        c = canonical(category_text, CATEGORIES)
        if c is None:
            errors.append({"field": "category", "message": "Unknown category '%s'" % category_text.strip()[:40]})
        else:
            clean["category"] = c

    return clean, errors


def resolve_headers(preset_name, overrides):
    if preset_name not in PRESETS:
        raise ImportFileError("Unknown column layout '%s'" % preset_name)
    preset = PRESETS[preset_name]
    headers = dict(preset["headers"])
    for key, value in (overrides or {}).items():
        if key not in headers:
            raise ImportFileError("Unknown column '%s' in mapping" % key)
        headers[key] = value
    return preset, headers


def _amount_and_direction(preset_name, cells):
    """Return (amount_minor positive or None, direction or None, errors)."""
    errors = []
    if preset_name == "debit_credit":
        debit = (cells.get("debit") or "").strip()
        credit = (cells.get("credit") or "").strip()
        if debit and credit:
            return None, None, [{"field": "amount", "message": "Both debit and credit are filled"}]
        if not debit and not credit:
            return None, None, [{"field": "amount", "message": "Neither debit nor credit is filled"}]
        direction = DIRECTION_DEBIT if debit else DIRECTION_CREDIT
        try:
            value = parse_amount(debit or credit)
        except ValueError as exc:
            return None, direction, [{"field": "amount", "message": str(exc)}]
        if value < 0:
            return None, direction, [{"field": "amount", "message": "Debit and credit amounts must be positive"}]
        return value, direction, errors

    try:
        value = parse_amount(cells.get("amount"))
    except ValueError as exc:
        return None, None, [{"field": "amount", "message": str(exc)}]
    direction_text = (cells.get("direction") or "").strip()
    if cells.get("direction") is not None:
        direction = DIRECTION_WORDS.get(direction_text.casefold())
        if direction is None:
            return abs(value), None, [{"field": "direction", "message": "Direction '%s' is not credit/debit" % direction_text[:20]}]
        if value < 0:
            return None, direction, [{"field": "amount", "message": "Amount must be positive when a direction column is used"}]
        return value, direction, errors
    # No direction column: positive is money in, negative is money out.
    return abs(value), (DIRECTION_CREDIT if value > 0 else DIRECTION_DEBIT), errors


def parse_csv(data, preset_name="signed_amount", overrides=None, max_rows=5000):
    """
    Parse CSV bytes. Returns dict: rows (list of row dicts), encoding.
    Raises ImportFileError for file-level problems. Bad rows are returned
    with errors, never dropped.
    """
    preset, headers = resolve_headers(preset_name, overrides)
    text, encoding = decode_bytes(data)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)

    try:
        header_row = next(reader)
    except StopIteration:
        raise ImportFileError("File is empty")
    except csv.Error as exc:
        raise ImportFileError("Malformed CSV header: %s" % exc)

    header_index = {}
    for i, name in enumerate(header_row):
        header_index.setdefault(name.strip().casefold(), i)

    columns = {}
    missing = []
    for key in preset["required"]:
        idx = header_index.get(headers[key].casefold())
        if idx is None:
            missing.append(headers[key])
        columns[key] = idx
    if missing:
        raise ImportFileError("Missing required column(s): " + ", ".join(missing))
    for key in preset["optional"]:
        columns[key] = header_index.get(headers[key].casefold())

    rows = []
    record_number = 1
    while True:
        try:
            record = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            raise ImportFileError("Malformed CSV near row %d: %s" % (record_number + 1, exc))
        record_number += 1
        if not any(cell.strip() for cell in record):
            continue
        if len(rows) >= max_rows:
            raise ImportFileError("File has more than %d rows" % max_rows)
        rows.append(_parse_record(record_number, record, header_row, columns, preset_name))

    if not rows:
        raise ImportFileError("File has a header but no data rows")
    return {"rows": rows, "encoding": encoding}


def _parse_record(row_number, record, header_row, columns, preset_name):
    raw = {}
    for i, value in enumerate(record):
        key = header_row[i].strip() if i < len(header_row) else "extra_%d" % i
        raw[key] = value[:MAX_CELL_LENGTH]

    if len(record) != len(header_row):
        message = "Row has %d columns, expected %d" % (len(record), len(header_row))
        return {"source_row_number": row_number, "raw": raw, "description": "",
                "original_description": "", "transaction_date": None, "amount_minor": None,
                "direction": None, "currency": CURRENCY, "transaction_type": None,
                "category": None, "errors": [{"field": "row", "message": message}]}

    cells = {}
    for key, idx in columns.items():
        cells[key] = record[idx] if idx is not None else None

    amount_minor, direction, amount_errors = _amount_and_direction(preset_name, cells)
    clean, errors = check_values(cells.get("description"), cells.get("date"), amount_minor,
                                 direction, cells.get("currency"), cells.get("type"), cells.get("category"))
    # Replace the generic amount/direction messages with the specific ones.
    if amount_errors:
        errors = [e for e in errors if e["field"] not in ("amount", "direction")] + amount_errors
    return {"source_row_number": row_number, "raw": raw,
            "original_description": (cells.get("description") or "").strip()[:MAX_CELL_LENGTH],
            "errors": errors, **clean}
