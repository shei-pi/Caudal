from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.schemas.analytics import (
    CategorySpend,
    MonthlySummaryItem,
    MonthlySummaryResponse,
    SpendingByCategoryResponse,
)


def get_spending_by_category(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
) -> SpendingByCategoryResponse:
    today = date.today()
    if not date_from:
        date_from = today.replace(day=1)
    if not date_to:
        date_to = today

    q = db.query(Transaction).filter(
        Transaction.tx_type == "debit",
        Transaction.date >= date_from,
        Transaction.date <= date_to,
    )
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    transactions = q.all()

    totals: dict[int | None, float] = {}
    counts: dict[int | None, int] = {}
    for tx in transactions:
        key = tx.category_id
        totals[key] = totals.get(key, 0) + tx.amount
        counts[key] = counts.get(key, 0) + 1

    total_ars = sum(totals.values())

    categories = {c.id: c for c in db.query(Category).all()}

    items = []
    for cat_id, total in sorted(totals.items(), key=lambda x: x[1], reverse=True):
        cat = categories.get(cat_id) if cat_id else None
        items.append(
            CategorySpend(
                category_id=cat_id,
                category_name=cat.name if cat else "Sin categorizar",
                color=cat.color if cat else "#9CA3AF",
                total_ars=round(total, 2),
                total_usd=None,
                transaction_count=counts[cat_id],
                percentage=round(total / total_ars * 100, 1) if total_ars > 0 else 0,
            )
        )

    return SpendingByCategoryResponse(
        items=items,
        total_ars=round(total_ars, 2),
        date_from=str(date_from),
        date_to=str(date_to),
    )


def get_monthly_summary(db: Session, months: int = 12) -> MonthlySummaryResponse:
    today = date.today()
    items = []

    for i in range(months - 1, -1, -1):
        first_day = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        if first_day.month == 12:
            last_day = first_day.replace(year=first_day.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)

        txs = db.query(Transaction).filter(
            Transaction.date >= first_day,
            Transaction.date <= last_day,
        ).all()

        income = sum(tx.amount for tx in txs if tx.tx_type == "credit")
        expense = sum(tx.amount for tx in txs if tx.tx_type == "debit")
        month_names = [
            "", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
        ]
        items.append(
            MonthlySummaryItem(
                year=first_day.year,
                month=first_day.month,
                label=f"{month_names[first_day.month]} {first_day.year}",
                income_ars=round(income, 2),
                expense_ars=round(expense, 2),
                net_ars=round(income - expense, 2),
            )
        )

    return MonthlySummaryResponse(items=items)
