# TODO: implement app/ingestion/parsers/naranja_x.py (NaranjaXParser)
# Naranja X is a credit card — all parsed rows are tx_type="debit" (purchases = expenses).
# Text format per line: "01/04  PEDIDOS YA BUENOS AIRES     $2.500,00"
# Pattern: r'(\d{2}/\d{2})\s{2,}(.+?)\s{2,}\$\s*([\d.,]+)'

from datetime import date
from unittest.mock import MagicMock, patch

from app.ingestion.parsers.naranja_x import NaranjaXParser


def _make_naranja_pdf_mock(text: str, year: int = 2025) -> MagicMock:
    """Build a pdfplumber context-manager mock for Naranja X text-based PDFs."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = text
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.metadata = {"CreationDate": f"D:{year}0401120000"}
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


def test_naranja_can_parse_identifies_naranja_text():
    parser = NaranjaXParser()
    assert parser.can_parse("NARANJA X\nResumen de cuenta Tarjeta Visa") is True


def test_naranja_cannot_parse_galicia():
    parser = NaranjaXParser()
    assert parser.can_parse("BANCO GALICIA S.A.\nCuenta Corriente") is False


def test_naranja_all_parsed_rows_are_debit():
    text = (
        "NARANJA X\n"
        "01/04  PEDIDOS YA BUENOS AIRES     $2.500,00\n"
        "05/04  SPOTIFY ARGENTINA           $799,00\n"
        "10/04  MERCADO LIBRE SA            $12.300,00\n"
    )
    mock_pdf = _make_naranja_pdf_mock(text, year=2025)
    parser = NaranjaXParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 3
    assert all(row.tx_type == "debit" for row in result)


def test_naranja_parses_amount_with_peso_sign():
    text = (
        "NARANJA X\n"
        "01/04  PEDIDOS YA BUENOS AIRES     $2.500,00\n"
    )
    mock_pdf = _make_naranja_pdf_mock(text, year=2025)
    parser = NaranjaXParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].amount == 2500.0


def test_naranja_parses_date_ddmm_uses_pdf_year():
    text = (
        "NARANJA X\n"
        "01/04  PEDIDOS YA BUENOS AIRES     $2.500,00\n"
    )
    mock_pdf = _make_naranja_pdf_mock(text, year=2025)
    parser = NaranjaXParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].transaction_date == date(2025, 4, 1)


def test_naranja_skips_non_matching_lines():
    text = (
        "NARANJA X\n"
        "Resumen de Cuenta - Período Abril 2025\n"
        "Fecha  Descripción  Importe\n"
        "TOTAL DEL PERÍODO:  $15.799,00\n"
        "01/04  PEDIDOS YA BUENOS AIRES     $2.500,00\n"
        "Vencimiento: 30/04/2025\n"
    )
    mock_pdf = _make_naranja_pdf_mock(text, year=2025)
    parser = NaranjaXParser()
    with patch("pdfplumber.open", return_value=mock_pdf):
        result = parser.parse("dummy.pdf")

    assert len(result) == 1
    assert result[0].description == "PEDIDOS YA BUENOS AIRES"
