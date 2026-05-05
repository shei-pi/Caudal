# TODO: implement app/ingestion/parsers/galicia.py (GaliciaParser)
# Galicia CA/CC table format:
#   Columns: FECHA | CONCEPTO | DÉBITO | CRÉDITO | SALDO
#   Row example: ["01/04/2025", "COMPRA DEBITO CARREFOUR", "3500,00", "", "50000,00"]
# parse() returns a ParseResult with:
#   - rows: list[ParsedRow]
#   - statement_total: closing_balance - opening_balance (extracted from "SALDO ANTERIOR" / "SALDO FINAL")
#   - total_kind: "balance_diff" — validation: sum(credits) - sum(debits) == closing - opening

from datetime import date
from unittest.mock import MagicMock, patch

from app.ingestion.parsers.galicia import GaliciaParser


def _make_pdf_mock(pages_tables: list[list[list]], header_text: str = "BANCO GALICIA") -> MagicMock:
    """Build a pdfplumber context-manager mock returning the given table rows per page."""
    mock_pdf = MagicMock()
    mock_pages = []
    for i, tables in enumerate(pages_tables):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = header_text if i == 0 else "BANCO GALICIA"
        mock_page.extract_tables.return_value = [tables] if tables else []
        mock_pages.append(mock_page)
    mock_pdf.pages = mock_pages
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


def test_galicia_can_parse_identifies_galicia_text():
    parser = GaliciaParser()
    assert parser.can_parse("BANCO GALICIA S.A. — Estado de Cuenta") is True


def test_galicia_cannot_parse_other_bank():
    parser = GaliciaParser()
    assert parser.can_parse("BANCO SANTANDER ARGENTINA") is False


def test_galicia_parses_debit_column_as_expense():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["01/04/2025", "COMPRA DEBITO CARREFOUR", "3500,00", "", "50000,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result.rows) == 1
    assert result.rows[0].tx_type == "debit"
    assert result.rows[0].amount == 3500.0
    assert result.rows[0].description == "COMPRA DEBITO CARREFOUR"


def test_galicia_parses_credit_column_as_income():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["02/04/2025", "DEPOSITO EN EFECTIVO", "", "15000,00", "65000,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result.rows) == 1
    assert result.rows[0].tx_type == "credit"
    assert result.rows[0].amount == 15000.0


def test_galicia_parses_argentine_number_format():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["03/04/2025", "SUPERMERCADO DISCO", "1.500,00", "", "48500,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result.rows) == 1
    assert result.rows[0].amount == 1500.0


def test_galicia_parses_date_ddmmyyyy():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["15/04/2025", "PAGO SERVICIO LUZ", "2000,00", "", "46500,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result.rows) == 1
    assert result.rows[0].transaction_date == date(2025, 4, 15)


def test_galicia_skips_rows_without_valid_date():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["", "TOTAL DEL PERIODO", "5000,00", "", ""],
        ["SALDO ANTERIOR", "", "", "", "45000,00"],
        ["10/04/2025", "COMPRA ONLINE", "800,00", "", "44200,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result.rows) == 1
    assert result.rows[0].transaction_date == date(2025, 4, 10)


def test_galicia_returns_empty_result_when_no_tables():
    mock_pdf = _make_pdf_mock([[]])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result.rows == []


# --------------------------------------------------------------------------- #
#  Statement total extraction (for validation)                                #
# --------------------------------------------------------------------------- #

def test_galicia_extracts_balance_diff_as_statement_total():
    # Caja de ahorro: opening 45000, three movements, closing 56700
    # closing - opening = 11700 → must equal credits - debits in rows
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["SALDO ANTERIOR", "", "", "", "45.000,00"],
        ["01/04/2025", "COMPRA CARREFOUR", "3.500,00", "", "41.500,00"],
        ["05/04/2025", "DEPOSITO SUELDO", "", "20.000,00", "61.500,00"],
        ["20/04/2025", "PAGO SERVICIO", "4.800,00", "", "56.700,00"],
        ["SALDO FINAL", "", "", "", "56.700,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result.total_kind == "balance_diff"
    assert result.statement_total == 11700.0  # closing - opening


def test_galicia_statement_total_none_when_balances_missing():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["10/04/2025", "COMPRA ONLINE", "800,00", "", "44200,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result.statement_total is None
