from datetime import datetime

from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    instrument_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # cedear, stock, bond, fci, crypto, usdt, currency
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="ARS")
    exchange: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_price_ars: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    holdings: Mapped[list["Holding"]] = relationship(  # noqa: F821
        "Holding", back_populates="instrument"
    )
