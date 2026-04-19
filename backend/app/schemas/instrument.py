from datetime import datetime

from pydantic import BaseModel, ConfigDict


class InstrumentBase(BaseModel):
    ticker: str
    name: str
    instrument_type: str
    currency: str = "ARS"
    exchange: str | None = None
    isin: str | None = None
    notes: str | None = None


class InstrumentCreate(InstrumentBase):
    pass


class InstrumentUpdate(BaseModel):
    name: str | None = None
    instrument_type: str | None = None
    currency: str | None = None
    exchange: str | None = None
    isin: str | None = None
    notes: str | None = None


class InstrumentRead(InstrumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_price: float | None
    last_price_ars: float | None
    last_price_usd: float | None
    last_updated: datetime | None
