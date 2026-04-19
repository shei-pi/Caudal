import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.categorization_rule import CategorizationRule
from app.models.transaction import Transaction
from app.schemas.categorization_rule import (
    RuleCreate,
    RuleRead,
    RuleTestRequest,
    RuleTestResult,
    RuleUpdate,
)

router = APIRouter(prefix="/api/rules", tags=["rules"])


@router.get("", response_model=list[RuleRead])
def list_rules(db: Session = Depends(get_db)):
    return (
        db.query(CategorizationRule)
        .order_by(CategorizationRule.priority.desc(), CategorizationRule.id)
        .all()
    )


@router.post("", response_model=RuleRead, status_code=201)
def create_rule(data: RuleCreate, db: Session = Depends(get_db)):
    rule = CategorizationRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=RuleRead)
def update_rule(rule_id: int, data: RuleUpdate, db: Session = Depends(get_db)):
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(CategorizationRule).filter(CategorizationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


@router.post("/test", response_model=RuleTestResult)
def test_rule(data: RuleTestRequest, db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()
    matched = []
    for tx in transactions:
        field_value = (
            tx.description_normalized
            if data.match_field == "description_normalized"
            else tx.description
        )
        hit = False
        if data.match_type == "contains":
            hit = data.pattern.upper() in field_value.upper()
        elif data.match_type == "startswith":
            hit = field_value.upper().startswith(data.pattern.upper())
        elif data.match_type == "regex":
            try:
                hit = bool(re.search(data.pattern, field_value, re.IGNORECASE))
            except re.error:
                raise HTTPException(status_code=400, detail="Invalid regex pattern")
        if hit:
            matched.append(
                {"id": tx.id, "date": str(tx.date), "description": tx.description, "amount": tx.amount}
            )
            if len(matched) >= data.limit:
                break
    return RuleTestResult(matched_count=len(matched), samples=matched)
