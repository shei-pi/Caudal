from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    __table_args__ = (UniqueConstraint("date", "rate_type", "source", name="uq_rate_date_type"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rate_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # oficial, blue, mep, ccl, cripto, mayorista, tarjeta
    currency_from: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    currency_to: Mapped[str] = mapped_column(String(10), nullable=False, default="ARS")
    buy_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    mid_rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="dolarapi")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
