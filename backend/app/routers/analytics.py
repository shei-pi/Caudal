from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.analytics import MonthlySummaryResponse, NetWorthResponse, SpendingByCategoryResponse
from app.services.net_worth import compute_net_worth
from app.services.spending import get_monthly_summary, get_spending_by_category

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/spending-by-category", response_model=SpendingByCategoryResponse)
def spending_by_category(
    date_from: date | None = None,
    date_to: date | None = None,
    account_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_spending_by_category(db, date_from=date_from, date_to=date_to, account_id=account_id)


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def monthly_summary(months: int = 12, db: Session = Depends(get_db)):
    return get_monthly_summary(db, months=months)


@router.get("/net-worth", response_model=NetWorthResponse)
def net_worth(db: Session = Depends(get_db)):
    return compute_net_worth(db)
