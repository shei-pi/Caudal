from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountBase(BaseModel):
    name: str
    institution: str
    currency: str = "ARS"
    account_type: str = "checking"
    current_balance: float = 0.0
    is_active: bool = True
    notes: str | None = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = None
    institution: str | None = None
    currency: str | None = None
    account_type: str | None = None
    current_balance: float | None = None
    is_active: bool | None = None
    notes: str | None = None


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
