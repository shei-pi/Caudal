from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ImportJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    bank: str | None
    status: str
    total_rows: int | None
    imported_rows: int | None
    duplicate_rows: int | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ImportPreview(BaseModel):
    job_id: int
    bank: str | None
    file_type: str
    rows: list[dict]
    columns: list[str]
    detected_account_id: int | None = None


class CsvColumnMapping(BaseModel):
    job_id: int
    account_id: int
    column_date: str
    column_description: str
    column_amount: str
    column_tx_type: str | None = None
    column_credit: str | None = None
    column_debit: str | None = None
    date_format: str = "%d/%m/%Y"
    currency: str = "ARS"


class ImportConfirm(BaseModel):
    account_id: int
    mapping: CsvColumnMapping | None = None
