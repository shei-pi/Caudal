from app.ingestion.base import BaseParser
from app.ingestion.parsers.galicia import GaliciaParser
from app.ingestion.parsers.galicia_visa import GaliciaVisaParser
from app.ingestion.parsers.generic import GenericParser
from app.ingestion.parsers.mercado_pago import MercadoPagoParser
from app.ingestion.parsers.naranja_x import NaranjaXParser

# Order matters: more specific parsers must come before general ones.
# GaliciaVisaParser must precede GaliciaParser (both match "GALICIA").
_PARSERS: list[BaseParser] = [
    GaliciaVisaParser(),
    GaliciaParser(),
    NaranjaXParser(),
    MercadoPagoParser(),
    GenericParser(),
]


def detect_bank(text: str) -> BaseParser:
    for parser in _PARSERS:
        if parser.can_parse(text):
            return parser
    return GenericParser()
