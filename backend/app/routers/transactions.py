import hashlib
import math
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCategorizeRequest,
    TransactionCreate,
    TransactionFilter,
    TransactionPage,
    TransactionRead,
    TransactionUpdate,
)
from app.services.categorization import apply_rules
from app.utils.text import normalize_description

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def _make_fingerprint(tx_date: date, desc_norm: str, amount: float, account_id: int) -> str:
    raw = f"{tx_date}|{desc_norm}|{round(amount, 2)}|{account_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.get("", response_model=TransactionPage)
def list_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    tx_type: str | None = None,
    is_recurring: bool | None = None,
    is_anomaly: bool | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_id is not None:
        q = q.filter(Transaction.category_id == category_id)
    if date_from:
        q = q.filter(Transaction.transaction_date >= date_from)
    if date_to:
        q = q.filter(Transaction.transaction_date <= date_to)
    if tx_type:
        q = q.filter(Transaction.tx_type == tx_type)
    if is_recurring is not None:
        q = q.filter(Transaction.is_recurring == is_recurring)
    if is_anomaly is not None:
        q = q.filter(Transaction.is_anomaly == is_anomaly)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                Transaction.description.ilike(pattern),
                Transaction.description_normalized.ilike(pattern),
            )
        )

    total = q.count()
    items = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return TransactionPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    if data.tx_type == "transfer":
        if not data.to_account_id:
            raise HTTPException(status_code=422, detail="to_account_id es requerido para transferencias")
        return _create_transfer(data, db)

    desc_norm = normalize_description(data.description)
    fingerprint = _make_fingerprint(data.transaction_date, desc_norm, data.amount, data.account_id)

    existing = db.query(Transaction).filter(Transaction.hash_fingerprint == fingerprint).first()
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate transaction detected")

    tx = Transaction(
        **data.model_dump(exclude={"to_account_id"}),
        description_normalized=desc_norm,
        hash_fingerprint=fingerprint,
        source="manual",
    )
    db.add(tx)
    db.flush()

    if tx.category_id is None:
        tx.category_id = apply_rules(db, tx)

    db.commit()
    db.refresh(tx)
    return tx


def _create_transfer(data: TransactionCreate, db: Session) -> Transaction:
    from app.models.account import Account as AccountModel

    source = db.query(AccountModel).filter(AccountModel.id == data.account_id).first()
    dest = db.query(AccountModel).filter(AccountModel.id == data.to_account_id).first()
    if not source or not dest:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    tid = str(uuid.uuid4())
    base = data.model_dump(exclude={"to_account_id", "tx_type", "description"})

    desc_out = data.description or f"Transferencia a {dest.name}"
    desc_in = data.description or f"Transferencia desde {source.name}"

    tx_out = Transaction(
        **base,
        account_id=data.account_id,
        tx_type="transfer",
        description=desc_out,
        description_normalized=normalize_description(desc_out),
        hash_fingerprint=_make_fingerprint(data.transaction_date, normalize_description(desc_out), data.amount, data.account_id),
        transfer_id=tid,
        source="manual",
    )
    tx_in = Transaction(
        **base,
        account_id=data.to_account_id,
        tx_type="transfer",
        description=desc_in,
        description_normalized=normalize_description(desc_in),
        hash_fingerprint=_make_fingerprint(data.transaction_date, normalize_description(desc_in), data.amount, data.to_account_id),
        transfer_id=tid,
        source="manual",
    )
    db.add(tx_out)
    db.add(tx_in)
    db.commit()
    db.refresh(tx_out)
    return tx_out


@router.get("/recurring", response_model=list[TransactionRead])
def list_recurring(db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .filter(Transaction.is_recurring == True)  # noqa: E712
        .order_by(Transaction.transaction_date.desc())
        .limit(200)
        .all()
    )


@router.get("/anomalies", response_model=list[TransactionRead])
def list_anomalies(db: Session = Depends(get_db)):
    return (
        db.query(Transaction)
        .filter(Transaction.is_anomaly == True)  # noqa: E712
        .order_by(Transaction.transaction_date.desc())
        .limit(100)
        .all()
    )


@router.get("/{tx_id}", response_model=TransactionRead)
def get_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.put("/{tx_id}", response_model=TransactionRead)
def update_transaction(tx_id: int, data: TransactionUpdate, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tx, field, value)
    if "description" in data.model_fields_set:
        tx.description_normalized = normalize_description(tx.description)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if tx.transfer_id:
        db.query(Transaction).filter(Transaction.transfer_id == tx.transfer_id).delete()
    else:
        db.delete(tx)
    db.commit()


@router.post("/{tx_id}/categorize", response_model=TransactionRead)
def categorize_transaction(
    tx_id: int, data: TransactionCategorizeRequest, db: Session = Depends(get_db)
):
    from app.models.categorization_rule import CategorizationRule

    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    tx.category_id = data.category_id
    if data.create_rule and data.rule_pattern:
        rule = CategorizationRule(
            category_id=data.category_id,
            pattern=data.rule_pattern,
            match_type=data.rule_match_type,
        )
        db.add(rule)
    db.commit()
    db.refresh(tx)
    return tx


@router.post("/run-categorization")
def run_categorization(db: Session = Depends(get_db)):
    uncategorized = (
        db.query(Transaction).filter(Transaction.category_id == None).all()  # noqa: E711
    )
    updated = 0
    for tx in uncategorized:
        cat_id = apply_rules(db, tx)
        if cat_id:
            tx.category_id = cat_id
            updated += 1
    db.commit()
    return {"updated": updated, "total_checked": len(uncategorized)}


@router.post("/run-recurrence")
def run_recurrence(db: Session = Depends(get_db)):
    from app.services.recurrence import detect_recurring

    count = detect_recurring(db)
    return {"flagged": count}


@router.post("/run-anomaly")
def run_anomaly(db: Session = Depends(get_db)):
    from app.services.anomaly import detect_anomalies

    count = detect_anomalies(db)
    return {"flagged": count}
