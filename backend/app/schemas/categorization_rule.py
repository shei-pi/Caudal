from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RuleBase(BaseModel):
    category_id: int
    pattern: str
    match_field: str = "description_normalized"
    match_type: str = "contains"
    priority: int = 0
    is_active: bool = True


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    category_id: int | None = None
    pattern: str | None = None
    match_field: str | None = None
    match_type: str | None = None
    priority: int | None = None
    is_active: bool | None = None


class RuleRead(RuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class RuleTestRequest(BaseModel):
    pattern: str
    match_type: str = "contains"
    match_field: str = "description_normalized"
    limit: int = 20


class RuleTestResult(BaseModel):
    matched_count: int
    samples: list[dict]
