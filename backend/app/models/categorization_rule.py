from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CategorizationRule(Base):
    __tablename__ = "categorization_rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False)
    pattern: Mapped[str] = mapped_column(String(300), nullable=False)
    match_field: Mapped[str] = mapped_column(
        String(50), nullable=False, default="description_normalized"
    )
    match_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="contains"
    )  # contains, startswith, regex
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped["Category"] = relationship(  # noqa: F821
        "Category", back_populates="rules"
    )
