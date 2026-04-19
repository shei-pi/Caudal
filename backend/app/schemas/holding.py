from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.instrument import InstrumentRead


class HoldingBase(BaseModel):
    instrument_id: int
    account_id: int
    quantity: float
    average_buy_price: float
    average_buy_price_ars: float | None = None
    average_buy_price_usd: float | None = None
    notes: str | None = None


class HoldingCreate(HoldingBase):
    pass


class HoldingUpdate(BaseModel):
    quantity: float | None = None
    average_buy_price: float | None = None
    average_buy_price_ars: float | None = None
    average_buy_price_usd: float | None = None
    notes: str | None = None


class HoldingRead(HoldingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    current_value_ars: float | None
    current_value_usd: float | None
    updated_at: datetime
    instrument: InstrumentRead | None = None
