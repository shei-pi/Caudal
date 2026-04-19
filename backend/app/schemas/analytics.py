from pydantic import BaseModel


class CategorySpend(BaseModel):
    category_id: int | None
    category_name: str
    color: str
    total_ars: float
    total_usd: float | None
    transaction_count: int
    percentage: float


class SpendingByCategoryResponse(BaseModel):
    items: list[CategorySpend]
    total_ars: float
    date_from: str
    date_to: str


class MonthlySummaryItem(BaseModel):
    year: int
    month: int
    label: str
    income_ars: float
    expense_ars: float
    net_ars: float


class MonthlySummaryResponse(BaseModel):
    items: list[MonthlySummaryItem]


class NetWorthResponse(BaseModel):
    total_assets_ars: float
    total_liabilities_ars: float
    net_worth_ars: float
    total_assets_usd: float | None
    total_liabilities_usd: float | None
    net_worth_usd: float | None
    accounts: list[dict]
    holdings_total_ars: float
    holdings_total_usd: float | None
