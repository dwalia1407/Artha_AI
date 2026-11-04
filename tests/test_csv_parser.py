import pytest

from app.imports.csv_parser import ImportFileError, parse_amount, parse_csv, parse_date


@pytest.mark.parametrize("text,paise", [("1,23,456.50", 12345650), ("(250.00)", -25000), ("-99.9", -9990),
                                        ("\u20b9 10", 1000), ("INR 5.05", 505), ("0.01", 1), ("100", 10000)])
def test_amount_parsing_is_exact(text, paise):
    assert parse_amount(text) == paise


@pytest.mark.parametrize("text", ["abc", "10.001", "", "0", "1e5", "NaN", "10 20", "999999999999999999"])
def test_bad_amounts_rejected(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def test_dates():
    assert str(parse_date("31/12/2025")) == "2025-12-31"
    assert str(parse_date("2025-11-02")) == "2025-11-02"
    assert str(parse_date("05-Nov-2026")) == "2026-11-05"
    for bad in ["31/02/2025", "2025-13-01", "", "yesterday", "1999-01-01"]:
        with pytest.raises(ValueError):
            parse_date(bad)


def rows_of(text, **kw):
    return parse_csv(text.encode(), **kw)["rows"]


def test_signed_amount_layout_direction_from_sign():
    r = rows_of("Date,Description,Amount\n2026-11-01,Salary,500.00\n2026-11-02,Tea,-12.50\n")
    assert (r[0]["direction"], r[0]["amount_minor"]) == ("credit", 50000)
    assert (r[1]["direction"], r[1]["amount_minor"]) == ("debit", 1250)
    assert r[0]["source_row_number"] == 2 and r[1]["source_row_number"] == 3


def test_direction_column_requires_positive_amount():
    r = rows_of("date,description,amount,direction\n2026-11-01,A,10,DR\n2026-11-01,B,-10,DR\n2026-11-01,C,10,sideways\n")
    assert r[0]["errors"] == [] and r[0]["direction"] == "debit"
    assert r[1]["errors"] and r[2]["errors"][0]["field"] == "direction"


def test_debit_credit_layout():
    r = rows_of("date,description,debit,credit\n2026-11-01,A,10.00,\n2026-11-01,B,,5\n2026-11-01,C,1,1\n2026-11-01,D,,\n",
                preset_name="debit_credit")
    assert r[0]["direction"] == "debit" and r[1]["direction"] == "credit"
    assert r[2]["errors"] and r[3]["errors"]


def test_missing_required_header_is_file_error():
    with pytest.raises(ImportFileError, match="amount"):
        parse_csv(b"date,description\n2026-11-01,x\n")


def test_custom_header_mapping():
    r = rows_of("Txn Date,Narration,Amt\n2026-11-01,Hi,5\n",
                overrides={"date": "Txn Date", "description": "Narration", "amount": "Amt"})
    assert r[0]["errors"] == []


def test_row_level_errors_are_kept_not_dropped():
    r = rows_of("date,description,amount,currency,category\n2026-13-01,x,5,INR,\n2026-11-01,,5,INR,\n"
                "2026-11-01,y,5,USD,\n2026-11-01,z,5,INR,Nonsense\n2026-11-01,ok,5,inr,groceries\n")
    assert [bool(x["errors"]) for x in r] == [True, True, True, True, False]
    assert r[0]["errors"][0]["field"] == "date"
    assert any(e["field"] == "currency" for e in r[2]["errors"])
    assert r[4]["category"] == "Groceries"


def test_wrong_column_count_row_is_invalid():
    r = rows_of("date,description,amount\n2026-11-01,x,5\n2026-11-01,too,many,cols\n")
    assert not r[0]["errors"] and r[1]["errors"][0]["field"] == "row"


def test_file_level_rejections():
    for data in [b"", b"date,description,amount\n", b"\x00\x01\x02binary", b"date,description,amount\n\"unterminated,1,2\n"]:
        with pytest.raises(ImportFileError):
            parse_csv(data)
    with pytest.raises(ImportFileError, match="more than 2"):
        parse_csv(b"date,description,amount\n2026-11-01,a,1\n2026-11-01,b,1\n2026-11-01,c,1\n", max_rows=2)
    with pytest.raises(ImportFileError):
        parse_csv(b"date,description,amount\n2026-11-01,a,1\n", preset_name="nope")


def test_encodings_and_bom():
    assert parse_csv("\ufeffdate,description,amount\n2026-11-01,caf\u00e9,1\n".encode("utf-8"))["encoding"] == "utf-8"
    r = parse_csv("date,description,amount\n2026-11-01,caf\u00e9,1\n".encode("cp1252"))
    assert r["encoding"] == "cp1252" and r["rows"][0]["description"] == "caf\u00e9"
    with pytest.raises(ImportFileError):
        parse_csv(b"date,description,amount\n2026-11-01,\x81\x8d,1\n")


def test_blank_lines_skipped_and_formula_text_kept_as_data():
    r = rows_of("date,description,amount\n\n2026-11-01,=SUM(A1),5\n")
    assert len(r) == 1 and r[0]["description"] == "=SUM(A1)"
