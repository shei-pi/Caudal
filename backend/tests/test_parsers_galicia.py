# TODO: implement app/ingestion/parsers/galicia.py (GaliciaParser)
# Galicia table format:
#   Columns: FECHA | CONCEPTO | DÉBITO | CRÉDITO | SALDO
#   Row example: ["01/04/2025", "COMPRA DEBITO CARREFOUR", "3500,00", "", "50000,00"]

from datetime import date
from unittest.mock import MagicMock, patch

from app.ingestion.parsers.galicia import GaliciaParser


def _make_pdf_mock(pages_tables: list[list[list]]) -> MagicMock:
    """Build a pdfplumber context-manager mock returning the given table rows per page."""
    mock_pdf = MagicMock()
    mock_pages = []
    for tables in pages_tables:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "BANCO GALICIA"
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

    assert len(result) == 1
    assert result[0].tx_type == "debit"
    assert result[0].amount == 3500.0
    assert result[0].description == "COMPRA DEBITO CARREFOUR"


def test_galicia_parses_credit_column_as_income():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["02/04/2025", "DEPOSITO EN EFECTIVO", "", "15000,00", "65000,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].tx_type == "credit"
    assert result[0].amount == 15000.0


def test_galicia_parses_argentine_number_format():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["03/04/2025", "SUPERMERCADO DISCO", "1.500,00", "", "48500,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].amount == 1500.0


def test_galicia_parses_date_ddmmyyyy():
    rows = [
        ["FECHA", "CONCEPTO", "DÉBITO", "CRÉDITO", "SALDO"],
        ["15/04/2025", "PAGO SERVICIO LUZ", "2000,00", "", "46500,00"],
    ]
    mock_pdf = _make_pdf_mock([rows])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].transaction_date == date(2025, 4, 15)


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

    assert len(result) == 1
    assert result[0].transaction_date == date(2025, 4, 10)


def test_galicia_returns_empty_list_when_no_tables():
    mock_pdf = _make_pdf_mock([[]])
    parser = GaliciaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result == []
