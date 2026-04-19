from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    rate_type: str
    currency_from: str
    currency_to: str
    buy_rate: float | None
    sell_rate: float | None
    mid_rate: float
    source: str
    fetched_at: datetime


class ExchangeRateLatest(BaseModel):
    oficial: ExchangeRateRead | None = None
    blue: ExchangeRateRead | None = None
    mep: ExchangeRateRead | None = None
    ccl: ExchangeRateRead | None = None
    cripto: ExchangeRateRead | None = None
    mayorista: ExchangeRateRead | None = None
    tarjeta: ExchangeRateRead | None = None


class ExchangeRateManual(BaseModel):
    date: date
    rate_type: str
    buy_rate: float | None = None
    sell_rate: float | None = None
    mid_rate: float
    currency_from: str = "USD"
    currency_to: str = "ARS"
