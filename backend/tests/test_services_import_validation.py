# TODO: implement app/services/import_validation.py
# Function: validate_import(parse_result: ParseResult) -> ValidationResult
# Compares the sum of parsed rows against the statement_total declared in the PDF.
#
# Behaviour by total_kind:
#   - "charges":      expected = sum(debits) - sum(credits)   (credit cards)
#   - "balance_diff": expected = sum(credits) - sum(debits)   (savings accounts)
#   - None / no total declared: returns is_valid=True with message "sin total declarado"
#
# Tolerance: 0.01 (one cent) — anything beyond is flagged as invalid.

from datetime import date

from app.ingestion.base import ParsedRow, ParseResult
from app.services.import_validation import ValidationResult, validate_import


def _row(amount: float, tx_type: str = "debit") -> ParsedRow:
    return ParsedRow(
        transaction_date=date(2025, 4, 1),
        description="X",
        amount=amount,
        tx_type=tx_type,
    )


# --------------------------------------------------------------------------- #
#  No total declared                                                          #
# --------------------------------------------------------------------------- #

def test_validation_passes_when_no_statement_total():
    result = ParseResult(rows=[_row(100), _row(200)], statement_total=None, total_kind=None)
    v = validate_import(result)
    assert v.is_valid is True
    assert v.expected is None


def test_validation_passes_when_total_kind_missing():
    result = ParseResult(rows=[_row(100)], statement_total=100.0, total_kind=None)
    v = validate_import(result)
    assert v.is_valid is True


# --------------------------------------------------------------------------- #
#  total_kind = "charges" (credit cards)                                      #
# --------------------------------------------------------------------------- #

def test_validation_passes_when_charges_match_total():
    rows = [_row(2500, "debit"), _row(850, "debit"), _row(12300, "debit")]
    result = ParseResult(rows=rows, statement_total=15650.0, total_kind="charges")
    v = validate_import(result)
    assert v.is_valid is True
    assert v.expected == 15650.0
    assert v.actual == 15650.0
    assert v.difference == 0.0


def test_validation_fails_when_charges_differ():
    # Rows sum to 3350 but statement says 3000 → diff 350
    rows = [_row(2500, "debit"), _row(850, "debit")]
    result = ParseResult(rows=rows, statement_total=3000.0, total_kind="charges")
    v = validate_import(result)
    assert v.is_valid is False
    assert v.difference == 350.0
    assert v.message is not None


def test_validation_charges_subtracts_card_payments():
    # Credit cards: payments to card are credit rows; net charges = debits - credits
    rows = [_row(10000, "debit"), _row(2000, "credit")]  # net = 8000
    result = ParseResult(rows=rows, statement_total=8000.0, total_kind="charges")
    v = validate_import(result)
    assert v.is_valid is True


# --------------------------------------------------------------------------- #
#  total_kind = "balance_diff" (savings accounts)                             #
# --------------------------------------------------------------------------- #

def test_validation_balance_diff_passes_for_savings_account():
    # Opening 45000, closing 56700 → diff 11700; rows: +20000 in, -3500 out, -4800 out = 11700
    rows = [
        _row(3500, "debit"),
        _row(20000, "credit"),
        _row(4800, "debit"),
    ]
    result = ParseResult(rows=rows, statement_total=11700.0, total_kind="balance_diff")
    v = validate_import(result)
    assert v.is_valid is True
    assert v.actual == 11700.0


def test_validation_balance_diff_fails_when_movements_dont_match():
    rows = [_row(1000, "debit"), _row(500, "credit")]  # net -500
    result = ParseResult(rows=rows, statement_total=200.0, total_kind="balance_diff")
    v = validate_import(result)
    assert v.is_valid is False


# --------------------------------------------------------------------------- #
#  Tolerance                                                                  #
# --------------------------------------------------------------------------- #

def test_validation_passes_within_one_cent_tolerance():
    rows = [_row(100.00, "debit"), _row(50.005, "debit")]  # sum 150.005
    result = ParseResult(rows=rows, statement_total=150.0, total_kind="charges")
    v = validate_import(result)
    assert v.is_valid is True


def test_validation_fails_beyond_one_cent_tolerance():
    rows = [_row(100.00, "debit"), _row(50.05, "debit")]  # sum 150.05, diff 0.05 > 0.01
    result = ParseResult(rows=rows, statement_total=150.0, total_kind="charges")
    v = validate_import(result)
    assert v.is_valid is False


# --------------------------------------------------------------------------- #
#  Result shape                                                               #
# --------------------------------------------------------------------------- #

def test_validation_result_exposes_all_fields():
    rows = [_row(1000, "debit")]
    result = ParseResult(rows=rows, statement_total=2000.0, total_kind="charges")
    v = validate_import(result)
    assert isinstance(v, ValidationResult)
    assert hasattr(v, "is_valid")
    assert hasattr(v, "expected")
    assert hasattr(v, "actual")
    assert hasattr(v, "difference")
    assert hasattr(v, "message")
