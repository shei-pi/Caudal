import re
from datetime import date

import pdfplumber

from app.ingestion.base import BaseParser, ParsedRow, ParseResult

_TOTAL_PATTERN = re.compile(r"TOTAL DEL PERIODO[:\s]+\$\s*([\d.,]+)", re.IGNORECASE)
_YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
_DATE_PATTERN = re.compile(r"^(\d{2})/(\d{2})$")


def _parse_ars(s: str) -> float | None:
    s = s.strip().lstrip("-")
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


class GaliciaVisaParser(BaseParser):
    bank_name = "Galicia"

    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "GALICIA" in upper and "VISA" in upper

    def parse(self, file_path: str) -> ParseResult:
        rows: list[ParsedRow] = []
        year: int | None = None
        statement_total: float | None = None
        all_text = ""

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                all_text += page_text + "\n"

                if year is None:
                    m = _YEAR_PATTERN.search(page_text)
                    if m:
                        year = int(m.group(1))

                for table in page.extract_tables():
                    for row in table:
                        if not row or len(row) < 4:
                            continue
                        fecha = (row[0] or "").strip()
                        establecimiento = (row[1] or "").strip()
                        importe_raw = (row[3] or "").strip()

                        m_date = _DATE_PATTERN.match(fecha)
                        if not m_date:
                            continue

                        day = int(m_date.group(1))
                        month = int(m_date.group(2))
                        effective_year = year or date.today().year
                        try:
                            tx_date = date(effective_year, month, day)
                        except ValueError:
                            continue

                        is_negative = importe_raw.startswith("-")
                        amount = _parse_ars(importe_raw)
                        if amount is None:
                            continue

                        tx_type = "credit" if is_negative else "debit"
                        rows.append(ParsedRow(
                            transaction_date=tx_date,
                            description=establecimiento,
                            amount=amount,
                            tx_type=tx_type,
                        ))

        m_total = _TOTAL_PATTERN.search(all_text)
        if m_total:
            statement_total = _parse_ars(m_total.group(1))

        return ParseResult(
            rows=rows,
            statement_total=statement_total,
            total_kind="charges" if statement_total is not None else None,
        )
