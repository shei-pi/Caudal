import re
from datetime import date

import pdfplumber

from app.ingestion.base import BaseParser, ParsedRow, ParseResult

_ROW_PATTERN = re.compile(r"(\d{2}/\d{2})\s{2,}(.+?)\s{2,}\$\s*([\d.,]+)")
_TOTAL_PATTERN = re.compile(r"TOTAL DEL PER[IÍ]ODO[:\s]*\$\s*([\d.,]+)", re.IGNORECASE)


def _parse_ars(s: str) -> float | None:
    s = s.strip().lstrip("-")
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


class NaranjaXParser(BaseParser):
    bank_name = "Naranja X"

    def can_parse(self, text: str) -> bool:
        return "NARANJA X" in text.upper()

    def parse(self, file_path: str) -> ParseResult:
        rows: list[ParsedRow] = []
        statement_total: float | None = None
        year: int | None = None

        with pdfplumber.open(file_path) as pdf:
            creation_date = (pdf.metadata or {}).get("CreationDate", "")
            if creation_date.startswith("D:") and len(creation_date) >= 6:
                try:
                    year = int(creation_date[2:6])
                except ValueError:
                    pass

            if year is None:
                year = date.today().year

            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"

        m_total = _TOTAL_PATTERN.search(full_text)
        if m_total:
            statement_total = _parse_ars(m_total.group(1))

        for line in full_text.splitlines():
            m = _ROW_PATTERN.match(line.strip())
            if not m:
                continue
            day_str, month_str = m.group(1).split("/")
            description = m.group(2).strip()
            amount = _parse_ars(m.group(3))
            if amount is None:
                continue
            try:
                tx_date = date(year, int(month_str), int(day_str))
            except ValueError:
                continue
            rows.append(ParsedRow(
                transaction_date=tx_date,
                description=description,
                amount=amount,
                tx_type="debit",
            ))

        return ParseResult(
            rows=rows,
            statement_total=statement_total,
            total_kind="charges" if statement_total is not None else None,
        )
