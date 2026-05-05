import csv
from datetime import datetime
from pathlib import Path

import pdfplumber

from app.ingestion.base import BaseParser, ParsedRow, ParseResult


class MercadoPagoParser(BaseParser):
    bank_name = "Mercado Pago"

    def can_parse(self, text: str) -> bool:
        return "MERCADO PAGO" in text.upper()

    def parse(self, file_path: str) -> ParseResult:
        ext = Path(file_path).suffix.lower()
        if ext == ".csv":
            return self._parse_csv(file_path)
        return self._parse_pdf(file_path)

    def _parse_csv(self, file_path: str) -> ParseResult:
        rows: list[ParsedRow] = []
        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                monto_str = row.get("Monto", "").strip()
                if not monto_str:
                    continue
                try:
                    amount_raw = float(monto_str)
                except ValueError:
                    continue
                amount = abs(amount_raw)
                tx_type = "debit" if amount_raw < 0 else "credit"

                fecha = row.get("Fecha", "").strip()
                try:
                    tx_date = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").date()
                except ValueError:
                    continue

                description = row.get("Descripción", "").strip()
                currency = row.get("Moneda", "ARS").strip() or "ARS"

                rows.append(ParsedRow(
                    transaction_date=tx_date,
                    description=description,
                    amount=amount,
                    tx_type=tx_type,
                    currency=currency,
                ))

        return ParseResult(rows=rows)

    def _parse_pdf(self, file_path: str) -> ParseResult:
        return ParseResult(rows=[])
