import re
from datetime import date

import pdfplumber

from app.ingestion.base import BaseParser, ParsedRow, ParseResult


def _parse_ars(s: str) -> float | None:
    s = s.strip().lstrip("-")
    if not s:
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _parse_date_ddmmyyyy(s: str) -> date | None:
    s = s.strip()
    parts = s.split("/")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except ValueError:
        return None


class GaliciaParser(BaseParser):
    bank_name = "Galicia"

    def can_parse(self, text: str) -> bool:
        upper = text.upper()
        return "GALICIA" in upper and "VISA" not in upper

    def parse(self, file_path: str) -> ParseResult:
        rows: list[ParsedRow] = []
        opening_balance: float | None = None
        closing_balance: float | None = None

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    for row in table:
                        if not row or len(row) < 5:
                            continue
                        fecha_cell = (row[0] or "").strip()
                        concepto = (row[1] or "").strip()
                        debito = (row[2] or "").strip()
                        credito = (row[3] or "").strip()
                        saldo = (row[4] or "").strip()

                        fecha_upper = fecha_cell.upper()
                        concepto_upper = concepto.upper()

                        if "SALDO ANTERIOR" in fecha_upper or "SALDO ANTERIOR" in concepto_upper:
                            opening_balance = _parse_ars(saldo)
                            continue
                        if "SALDO FINAL" in fecha_upper or "SALDO FINAL" in concepto_upper:
                            closing_balance = _parse_ars(saldo)
                            continue

                        tx_date = _parse_date_ddmmyyyy(fecha_cell)
                        if tx_date is None:
                            continue

                        if debito:
                            amount = _parse_ars(debito)
                            if amount is not None:
                                rows.append(ParsedRow(
                                    transaction_date=tx_date,
                                    description=concepto,
                                    amount=amount,
                                    tx_type="debit",
                                ))
                        elif credito:
                            amount = _parse_ars(credito)
                            if amount is not None:
                                rows.append(ParsedRow(
                                    transaction_date=tx_date,
                                    description=concepto,
                                    amount=amount,
                                    tx_type="credit",
                                ))

        statement_total = None
        if opening_balance is not None and closing_balance is not None:
            statement_total = round(closing_balance - opening_balance, 2)

        return ParseResult(
            rows=rows,
            statement_total=statement_total,
            total_kind="balance_diff" if statement_total is not None else None,
        )
