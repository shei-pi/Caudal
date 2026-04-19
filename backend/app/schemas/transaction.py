from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.category import CategoryRead


class TransactionBase(BaseModel):
    account_id: int
    date: date
    description: str
    amount: float
    tx_type: str  # debit, credit
    currency: str = "ARS"
    category_id: int | None = None
    notes: str | None = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    date: date | None = None
    description: str | None = None
    amount: float | None = None
    tx_type: str | None = None
    currency: str | None = None
    category_id: int | None = None
    notes: str | None = None


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description_normalized: str
    amount_ars: float | None
    amount_usd: float | None
    exchange_rate_used: float | None
    is_recurring: bool
    recurring_group_id: str | None
    is_anomaly: bool
    anomaly_score: float | None
    source: str
    import_job_id: int | None
    hash_fingerprint: str
    created_at: datetime
    updated_at: datetime
    category: CategoryRead | None = None


class TransactionCategorizeRequest(BaseModel):
    category_id: int
    create_rule: bool = False
    rule_pattern: str | None = None
    rule_match_type: str = "contains"


class TransactionFilter(BaseModel):
    account_id: int | None = None
    category_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    tx_type: str | None = None
    is_recurring: bool | None = None
    is_anomaly: bool | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 50


class TransactionPage(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    page_size: int
    pages: int
