import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def detect_anomalies(db: Session, contamination: float = 0.05) -> int:
    transactions = db.query(Transaction).filter(Transaction.tx_type == "debit").all()
    if len(transactions) < 10:
        return 0

    rows = [
        {
            "id": tx.id,
            "amount": tx.amount,
            "day_of_week": pd.Timestamp(tx.date).dayofweek,
            "category_id": tx.category_id or -1,
        }
        for tx in transactions
    ]
    df = pd.DataFrame(rows)

    # Z-score per category
    df["cat_mean"] = df.groupby("category_id")["amount"].transform("mean")
    df["cat_std"] = df.groupby("category_id")["amount"].transform("std").fillna(1)
    df["zscore"] = (df["amount"] - df["cat_mean"]) / df["cat_std"]

    features = df[["amount", "day_of_week", "zscore"]].fillna(0).values

    clf = IsolationForest(contamination=contamination, random_state=42)
    scores = clf.fit_predict(features)
    raw_scores = clf.score_samples(features)

    # Also flag simple statistical outliers (>3 std)
    hard_flag = np.abs(df["zscore"].values) > 3

    flagged_ids = set()
    score_map: dict[int, float] = {}
    for i, tx_row in df.iterrows():
        is_outlier = scores[i] == -1 or hard_flag[i]
        if is_outlier:
            tx_id = int(tx_row["id"])
            flagged_ids.add(tx_id)
            score_map[tx_id] = float(raw_scores[i])

    updated = 0
    tx_map = {tx.id: tx for tx in transactions}
    for tx in transactions:
        new_val = tx.id in flagged_ids
        if tx.is_anomaly != new_val:
            tx.is_anomaly = new_val
            tx.anomaly_score = score_map.get(tx.id)
            updated += 1

    db.commit()
    return updated
