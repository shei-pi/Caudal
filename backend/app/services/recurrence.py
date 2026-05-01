import re
import uuid

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def _normalize_for_recurrence(desc: str) -> str:
    """Strip amounts, dates and trailing digits to group similar descriptions."""
    s = desc.upper()
    s = re.sub(r"\d{2}/\d{2}(/\d{2,4})?", "", s)
    s = re.sub(r"\$\s*[\d.,]+", "", s)
    s = re.sub(r"\b\d+\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def detect_recurring(db: Session) -> int:
    transactions = db.query(Transaction).order_by(Transaction.transaction_date).all()
    if not transactions:
        return 0

    rows = [
        {
            "id": tx.id,
            "date": pd.Timestamp(tx.transaction_date),
            "account_id": tx.account_id,
            "amount": tx.amount,
            "tx_type": tx.tx_type,
            "key": f"{tx.account_id}|{_normalize_for_recurrence(tx.description_normalized)}",
        }
        for tx in transactions
    ]
    df = pd.DataFrame(rows)

    flagged_ids: set[int] = set()
    group_map: dict[int, str] = {}

    for key, group in df.groupby("key"):
        group = group.sort_values("date")
        if len(group) < 3:
            continue
        intervals = group["date"].diff().dt.days.dropna().values
        if len(intervals) == 0:
            continue
        mean_interval = float(np.mean(intervals))
        if mean_interval < 1:
            continue
        cv = float(np.std(intervals) / mean_interval) if mean_interval > 0 else 1.0
        amounts = group["amount"].values
        amount_cv = float(np.std(amounts) / np.mean(amounts)) if np.mean(amounts) > 0 else 1.0
        if cv < 0.3 and amount_cv < 0.20:
            group_id = str(uuid.uuid4())
            for tx_id in group["id"].values:
                flagged_ids.add(int(tx_id))
                group_map[int(tx_id)] = group_id

    updated = 0
    for tx in transactions:
        new_val = tx.id in flagged_ids
        if tx.is_recurring != new_val:
            tx.is_recurring = new_val
            tx.recurring_group_id = group_map.get(tx.id)
            updated += 1

    db.commit()
    return updated
