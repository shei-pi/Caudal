from app.ingestion.base import BaseParser, ParseResult


class GenericParser(BaseParser):
    bank_name = "Desconocido"

    def can_parse(self, text: str) -> bool:
        return True

    def parse(self, file_path: str) -> ParseResult:
        return ParseResult(rows=[])
