from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class ParsedRow:
    transaction_date: date
    description: str
    amount: float
    tx_type: str  # "debit" or "credit"
    currency: str = "ARS"
    notes: str | None = None


@dataclass
class ParseResult:
    rows: list[ParsedRow] = field(default_factory=list)
    statement_total: float | None = None
    total_kind: str | None = None  # "charges" or "balance_diff"
    period_start: date | None = None
    period_end: date | None = None


class BaseParser(ABC):
    bank_name: str = "Desconocido"

    @abstractmethod
    def can_parse(self, text: str) -> bool: ...

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult: ...
