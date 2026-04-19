from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    parent_id: int | None = None
    color: str = "#6B7280"
    icon: str | None = None
    is_income: bool = False


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    color: str | None = None
    icon: str | None = None
    is_income: bool | None = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_system: bool
    created_at: datetime


class CategoryTree(CategoryRead):
    children: list["CategoryTree"] = []
