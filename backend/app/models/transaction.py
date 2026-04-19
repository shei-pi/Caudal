from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    description_normalized: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    tx_type: Mapped[str] = mapped_column(String(10), nullable=False)  # debit, credit
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="ARS")
    amount_ars: Mapped[float | None] = mapped_column(Float, nullable=True)
    amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    exchange_rate_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, index=True
    )
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_group_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    import_job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("import_jobs.id"), nullable=True
    )
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hash_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    account: Mapped["Account"] = relationship(  # noqa: F821
        "Account", back_populates="transactions"
    )
    category: Mapped["Category | None"] = relationship(  # noqa: F821
        "Category", back_populates="transactions"
    )
    import_job: Mapped["ImportJob | None"] = relationship(  # noqa: F821
        "ImportJob", back_populates="transactions"
    )
