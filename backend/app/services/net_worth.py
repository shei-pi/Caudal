from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.holding import Holding
from app.schemas.analytics import NetWorthResponse


def compute_net_worth(db: Session) -> NetWorthResponse:
    accounts = db.query(Account).filter(Account.is_active == True).all()  # noqa: E712
    holdings = db.query(Holding).all()

    assets_ars = 0.0
    liabilities_ars = 0.0
    account_details = []

    for acc in accounts:
        balance = acc.current_balance
        is_liability = acc.account_type == "credit_card" and balance < 0
        account_details.append(
            {
                "id": acc.id,
                "name": acc.name,
                "currency": acc.currency,
                "balance": balance,
                "account_type": acc.account_type,
                "is_liability": is_liability,
            }
        )
        # Simple: treat all as ARS for now (Phase 3 will do proper conversion)
        if is_liability:
            liabilities_ars += abs(balance)
        else:
            assets_ars += balance

    holdings_total_ars = sum(h.current_value_ars or 0 for h in holdings)
    holdings_total_usd = sum(h.current_value_usd or 0 for h in holdings)
    assets_ars += holdings_total_ars

    return NetWorthResponse(
        total_assets_ars=assets_ars,
        total_liabilities_ars=liabilities_ars,
        net_worth_ars=assets_ars - liabilities_ars,
        total_assets_usd=None,
        total_liabilities_usd=None,
        net_worth_usd=None,
        accounts=account_details,
        holdings_total_ars=holdings_total_ars,
        holdings_total_usd=holdings_total_usd if holdings_total_usd > 0 else None,
    )
