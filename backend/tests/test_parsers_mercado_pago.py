# TODO: implement app/ingestion/parsers/mercado_pago.py (MercadoPagoParser)
# Mercado Pago primary format: CSV export from the app/website
# CSV columns: Fecha,Descripción,Tipo de operación,Monto,Moneda
# Monto: negative = expense (debit), positive = income (credit)
# Date format: "2025-04-15 10:30:00" (ISO datetime)
# Detection: text contains "MERCADO PAGO" (works for both PDF text and CSV header)
# parse() dispatches to _parse_csv() or _parse_pdf() based on file extension

import io
import textwrap
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.ingestion.parsers.mercado_pago import MercadoPagoParser


# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #

def _csv_content(*rows: str, header: str = "Fecha,Descripción,Tipo de operación,Monto,Moneda") -> str:
    """Build a minimal MP CSV string."""
    return "\n".join([header] + list(rows))


def _make_mp_pdf_mock(text: str = "MERCADO PAGO") -> MagicMock:
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = text
    mock_page.extract_tables.return_value = []
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)
    return mock_pdf


# --------------------------------------------------------------------------- #
#  can_parse                                                                  #
# --------------------------------------------------------------------------- #

def test_mercado_pago_can_parse_identifies_mercado_pago_text():
    parser = MercadoPagoParser()
    assert parser.can_parse("MERCADO PAGO S.A. — Estado de cuenta") is True


def test_mercado_pago_can_parse_case_insensitive():
    parser = MercadoPagoParser()
    assert parser.can_parse("Mercado Pago\nFecha,Descripción,Monto") is True


def test_mercado_pago_cannot_parse_unrelated_text():
    parser = MercadoPagoParser()
    assert parser.can_parse("BANCO GALICIA S.A. — RESUMEN VISA") is False


# --------------------------------------------------------------------------- #
#  CSV parsing                                                                #
# --------------------------------------------------------------------------- #

def test_mercado_pago_negative_amount_is_debit(tmp_path):
    csv_file = tmp_path / "mp.csv"
    csv_file.write_text(
        _csv_content("2025-04-15 10:30:00,Netflix,Suscripción,-1500.00,ARS"),
        encoding="utf-8",
    )
    parser = MercadoPagoParser()
    result = parser.parse(str(csv_file))

    assert len(result) == 1
    assert result[0].tx_type == "debit"
    assert result[0].amount == 1500.0


def test_mercado_pago_positive_amount_is_credit(tmp_path):
    csv_file = tmp_path / "mp.csv"
    csv_file.write_text(
        _csv_content("2025-04-14 15:20:00,Pago recibido de Juan,Cobros,2000.00,ARS"),
        encoding="utf-8",
    )
    parser = MercadoPagoParser()
    result = parser.parse(str(csv_file))

    assert len(result) == 1
    assert result[0].tx_type == "credit"
    assert result[0].amount == 2000.0


def test_mercado_pago_parses_iso_datetime_to_date(tmp_path):
    csv_file = tmp_path / "mp.csv"
    csv_file.write_text(
        _csv_content("2025-04-01 08:00:00,Supermercado,Pago,-3500.00,ARS"),
        encoding="utf-8",
    )
    parser = MercadoPagoParser()
    result = parser.parse(str(csv_file))

    assert result[0].transaction_date == date(2025, 4, 1)


def test_mercado_pago_parses_usd_currency(tmp_path):
    csv_file = tmp_path / "mp.csv"
    csv_file.write_text(
        _csv_content("2025-04-10 12:00:00,Binance transfer,Transferencia,-100.00,USD"),
        encoding="utf-8",
    )
    parser = MercadoPagoParser()
    result = parser.parse(str(csv_file))

    assert result[0].currency == "USD"


def test_mercado_pago_skips_rows_with_missing_amount(tmp_path):
    csv_file = tmp_path / "mp.csv"
    csv_file.write_text(
        _csv_content(
            "2025-04-01 08:00:00,Gasto válido,Pago,-500.00,ARS",
            "2025-04-02 09:00:00,Fila sin monto,Pago,,ARS",
        ),
        encoding="utf-8",
    )
    parser = MercadoPagoParser()
    result = parser.parse(str(csv_file))

    assert len(result) == 1
    assert result[0].description == "Gasto válido"


def test_mercado_pago_multiple_rows_parsed_in_order(tmp_path):
    csv_file = tmp_path / "mp.csv"
    csv_file.write_text(
        _csv_content(
            "2025-04-01 08:00:00,Compra A,Pago,-1000.00,ARS",
            "2025-04-02 09:00:00,Compra B,Pago,-2000.00,ARS",
            "2025-04-03 10:00:00,Ingreso C,Cobro,5000.00,ARS",
        ),
        encoding="utf-8",
    )
    parser = MercadoPagoParser()
    result = parser.parse(str(csv_file))

    assert len(result) == 3
    assert result[0].description == "Compra A"
    assert result[2].tx_type == "credit"


# --------------------------------------------------------------------------- #
#  Bank name                                                                  #
# --------------------------------------------------------------------------- #

def test_mercado_pago_bank_name_attribute():
    parser = MercadoPagoParser()
    assert "Mercado Pago" in parser.bank_name
