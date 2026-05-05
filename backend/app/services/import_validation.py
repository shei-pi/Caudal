from dataclasses import dataclass

from app.ingestion.base import ParseResult


@dataclass
class ValidationResult:
    is_valid: bool
    expected: float | None
    actual: float | None
    difference: float
    message: str | None


def validate_import(result: ParseResult) -> ValidationResult:
    if result.statement_total is None or result.total_kind is None:
        return ValidationResult(
            is_valid=True,
            expected=None,
            actual=None,
            difference=0,
            message="sin total declarado",
        )

    debits = sum(r.amount for r in result.rows if r.tx_type == "debit")
    credits = sum(r.amount for r in result.rows if r.tx_type == "credit")

    if result.total_kind == "charges":
        actual = debits - credits
    elif result.total_kind == "balance_diff":
        actual = credits - debits
    else:
        return ValidationResult(
            is_valid=True,
            expected=None,
            actual=None,
            difference=0,
            message="tipo de total desconocido",
        )

    expected = result.statement_total
    difference = round(abs(actual - expected), 2)
    is_valid = difference <= 0.01

    return ValidationResult(
        is_valid=is_valid,
        expected=expected,
        actual=round(actual, 2),
        difference=difference,
        message=None if is_valid else f"Diferencia de {difference} detectada",
    )
