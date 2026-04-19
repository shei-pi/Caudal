import re

from sqlalchemy.orm import Session

from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction


def apply_rules(db: Session, tx: Transaction) -> int | None:
    """Return category_id from first matching rule, or None."""
    rules = (
        db.query(CategorizationRule)
        .filter(CategorizationRule.is_active == True)  # noqa: E712
        .order_by(CategorizationRule.priority.desc())
        .all()
    )
    field_value = (
        tx.description_normalized
        if True  # always use normalized
        else tx.description
    )
    for rule in rules:
        pattern = rule.pattern.upper()
        target = field_value.upper()
        if rule.match_type == "contains" and pattern in target:
            return rule.category_id
        elif rule.match_type == "startswith" and target.startswith(pattern):
            return rule.category_id
        elif rule.match_type == "regex":
            try:
                if re.search(rule.pattern, field_value, re.IGNORECASE):
                    return rule.category_id
            except re.error:
                continue
    return None
