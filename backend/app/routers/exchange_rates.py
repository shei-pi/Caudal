from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.exchange_rate import ExchangeRate
from app.schemas.exchange_rate import ExchangeRateLatest, ExchangeRateManual, ExchangeRateRead
from app.services.exchange_rate_fetcher import fetch_and_store_rates

router = APIRouter(prefix="/api/exchange-rates", tags=["exchange-rates"])

RATE_TYPES = ["oficial", "blue", "mep", "ccl", "cripto", "mayorista", "tarjeta"]


@router.get("/latest", response_model=ExchangeRateLatest)
def get_latest_rates(db: Session = Depends(get_db)):
    result = {}
    for rt in RATE_TYPES:
        rate = (
            db.query(ExchangeRate)
            .filter(ExchangeRate.rate_type == rt)
            .order_by(ExchangeRate.date.desc(), ExchangeRate.fetched_at.desc())
            .first()
        )
        result[rt] = rate
    return ExchangeRateLatest(**result)


@router.get("/history", response_model=list[ExchangeRateRead])
def get_rate_history(
    rate_type: str = "blue",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ExchangeRate).filter(ExchangeRate.rate_type == rate_type)
    if date_from:
        q = q.filter(ExchangeRate.date >= date_from)
    if date_to:
        q = q.filter(ExchangeRate.date <= date_to)
    return q.order_by(ExchangeRate.date.desc()).limit(365).all()


@router.post("/refresh")
async def refresh_rates(db: Session = Depends(get_db)):
    stored = await fetch_and_store_rates(db)
    return {"stored": stored}


@router.post("/manual", response_model=ExchangeRateRead, status_code=201)
def add_manual_rate(data: ExchangeRateManual, db: Session = Depends(get_db)):
    from datetime import datetime

    rate = ExchangeRate(
        **data.model_dump(),
        source="manual",
        fetched_at=datetime.now(),
    )
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate
