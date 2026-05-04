# TODO: implement app/ingestion/parsers/galicia_visa.py (GaliciaVisaParser)
# Galicia Visa (tarjeta de crédito) PDF format:
#   Columns: FECHA | ESTABLECIMIENTO | CUOTAS | IMPORTE
#   Row example: ["01/04", "AMAZON.COM.BR", "1/1", "2.500,00"]
#   Date is dd/mm — year extracted from statement header text
#   All charges are tx_type="debit" (expenses); card payments are tx_type="credit"
#   Detection: text contains "GALICIA" AND "VISA" (distinguishes from CA/CC)

from datetime import date
from unittest.mock import MagicMock, patch

from app.ingestion.parsers.galicia_visa import GaliciaVisaParser


def _make_visa_pdf_mock(pages_tables: list[list[list]], header_text: str = "BANCO GALICIA VISA 2025") -> MagicMock:
    """Build a pdfplumber mock for Galicia Visa statements."""
    mock_pdf = MagicMock()
    mock_pages = []
    for i, tables in enumerate(pages_tables):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = header_text if i == 0 else "BANCO GALICIA VISA"
        mock_page.extract_tables.return_value = [tables] if tables else []
        mock_pages.append(mock_page)
    mock_pdf.pages = mock_pages
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


def test_galicia_visa_can_parse_when_text_contains_galicia_and_visa():
    parser = GaliciaVisaParser()
    assert parser.can_parse("BANCO GALICIA S.A. — RESUMEN VISA PLATINUM") is True


def test_galicia_visa_cannot_parse_galicia_ca_without_visa():
    # Galicia CA/CC does NOT say VISA — must not be matched by this parser
    parser = GaliciaVisaParser()
    assert parser.can_parse("BANCO GALICIA S.A. — CAJA DE AHORRO EN PESOS") is False


def test_galicia_visa_cannot_parse_other_bank():
    parser = GaliciaVisaParser()
    assert parser.can_parse("VISA SANTANDER ARGENTINA") is False


def test_galicia_visa_all_purchases_are_debit():
    rows = [
        ["FECHA", "ESTABLECIMIENTO", "CUOTAS", "IMPORTE"],
        ["01/04", "AMAZON.COM.BR", "1/1", "2.500,00"],
        ["03/04", "NETFLIX", "1/1", "850,00"],
    ]
    mock_pdf = _make_visa_pdf_mock([rows], header_text="BANCO GALICIA VISA 2025")
    parser = GaliciaVisaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 2
    assert all(r.tx_type == "debit" for r in result)


def test_galicia_visa_payment_to_card_is_credit():
    rows = [
        ["FECHA", "ESTABLECIMIENTO", "CUOTAS", "IMPORTE"],
        ["05/04", "PAGO TARJETA — GRACIAS", "", "-15.000,00"],
    ]
    mock_pdf = _make_visa_pdf_mock([rows], header_text="BANCO GALICIA VISA 2025")
    parser = GaliciaVisaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].tx_type == "credit"
    assert result[0].amount == 15000.0


def test_galicia_visa_parses_argentine_number_format():
    rows = [
        ["FECHA", "ESTABLECIMIENTO", "CUOTAS", "IMPORTE"],
        ["10/04", "SUPERMERCADO DISCO", "1/1", "12.350,50"],
    ]
    mock_pdf = _make_visa_pdf_mock([rows])
    parser = GaliciaVisaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result[0].amount == 12350.50


def test_galicia_visa_infers_year_from_header_text():
    # Header says 2025 — dates like "15/04" should become date(2025, 4, 15)
    rows = [
        ["FECHA", "ESTABLECIMIENTO", "CUOTAS", "IMPORTE"],
        ["15/04", "SPOTIFY", "1/1", "600,00"],
    ]
    mock_pdf = _make_visa_pdf_mock([rows], header_text="RESUMEN VISA BANCO GALICIA ABRIL 2025")
    parser = GaliciaVisaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result[0].transaction_date == date(2025, 4, 15)


def test_galicia_visa_skips_rows_without_valid_date():
    rows = [
        ["FECHA", "ESTABLECIMIENTO", "CUOTAS", "IMPORTE"],
        ["", "SALDO ANTERIOR", "", "50.000,00"],
        ["TOTAL", "DEL PERIODO", "", "14.950,50"],
        ["20/04", "UBER", "1/1", "1.200,00"],
    ]
    mock_pdf = _make_visa_pdf_mock([rows])
    parser = GaliciaVisaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].description == "UBER"


def test_galicia_visa_returns_empty_list_when_no_tables():
    mock_pdf = _make_visa_pdf_mock([[]])
    parser = GaliciaVisaParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert result == []
