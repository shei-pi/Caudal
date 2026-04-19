from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    average_buy_price_ars: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_buy_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value_ars: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    instrument: Mapped["Instrument"] = relationship(  # noqa: F821
        "Instrument", back_populates="holdings"
    )
    account: Mapped["Account"] = relationship(  # noqa: F821
        "Account", back_populates="holdings"
    )
