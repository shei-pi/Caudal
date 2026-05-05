# TODO: implement app/ingestion/base.py (ParsedRow dataclass, BaseParser ABC)
# TODO: implement app/ingestion/registry.py (detect_bank function)
# TODO: implement app/ingestion/parsers/galicia.py (GaliciaParser)
# TODO: implement app/ingestion/parsers/galicia_visa.py (GaliciaVisaParser)
# TODO: implement app/ingestion/parsers/naranja_x.py (NaranjaXParser)
# TODO: implement app/ingestion/parsers/mercado_pago.py (MercadoPagoParser)
# TODO: implement app/ingestion/parsers/generic.py (GenericParser)

from datetime import date

from app.ingestion.base import BaseParser, ParsedRow, ParseResult
from app.ingestion.parsers.galicia import GaliciaParser
from app.ingestion.parsers.galicia_visa import GaliciaVisaParser
from app.ingestion.parsers.generic import GenericParser
from app.ingestion.parsers.mercado_pago import MercadoPagoParser
from app.ingestion.parsers.naranja_x import NaranjaXParser
from app.ingestion.registry import detect_bank


def test_parsed_row_has_required_fields():
    row = ParsedRow(
        transaction_date=date(2025, 4, 1),
        description="CARREFOUR PALERMO",
        amount=3500.0,
        tx_type="debit",
    )
    assert row.transaction_date == date(2025, 4, 1)
    assert row.description == "CARREFOUR PALERMO"
    assert row.amount == 3500.0
    assert row.tx_type == "debit"


def test_parsed_row_currency_defaults_to_ars():
    row = ParsedRow(
        transaction_date=date(2025, 4, 1),
        description="PAGO SERVICIO",
        amount=1000.0,
        tx_type="credit",
    )
    assert row.currency == "ARS"
    assert row.notes is None


def test_parse_result_holds_rows_and_optional_total():
    rows = [
        ParsedRow(transaction_date=date(2025, 4, 1), description="X", amount=100.0, tx_type="debit"),
    ]
    result = ParseResult(rows=rows, statement_total=100.0, total_kind="charges")
    assert result.rows == rows
    assert result.statement_total == 100.0
    assert result.total_kind == "charges"


def test_parse_result_defaults_when_only_rows_provided():
    result = ParseResult(rows=[])
    assert result.statement_total is None
    assert result.total_kind is None
    assert result.period_start is None
    assert result.period_end is None


def test_detect_bank_returns_galicia_parser_for_galicia_text():
    text = "BANCO GALICIA S.A.\nEstado de cuenta\nCuenta Corriente"
    parser = detect_bank(text)
    assert isinstance(parser, GaliciaParser)


def test_detect_bank_returns_naranja_parser_for_naranja_text():
    text = "NARANJA X\nResumen de cuenta\nTarjeta de crédito"
    parser = detect_bank(text)
    assert isinstance(parser, NaranjaXParser)


def test_detect_bank_returns_galicia_visa_parser_for_galicia_visa_text():
    # Must match before generic Galicia CA/CC
    text = "BANCO GALICIA S.A. — RESUMEN VISA PLATINUM"
    parser = detect_bank(text)
    assert isinstance(parser, GaliciaVisaParser)


def test_detect_bank_returns_mercado_pago_parser_for_mp_text():
    text = "MERCADO PAGO S.A.\nFecha,Descripción,Monto"
    parser = detect_bank(text)
    assert isinstance(parser, MercadoPagoParser)


def test_detect_bank_returns_generic_parser_for_unknown_text():
    text = "BANCO DESCONOCIDO S.A.\nResumen de operaciones"
    parser = detect_bank(text)
    assert isinstance(parser, GenericParser)
