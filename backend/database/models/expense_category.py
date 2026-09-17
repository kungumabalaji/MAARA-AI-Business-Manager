from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, UUIDPrimaryKeyMixin


class ExpenseCategory(Base, UUIDPrimaryKeyMixin):
    """A row, not a column. organization_id NULL = system default, visible to every org.

    organization_id set = that org's own custom addition. Predefined categories and
    ad-hoc expense descriptions both live in daily_report_expenses; this table only
    supplies the predefined list and the fixed/variable classification.
    """

    __tablename__ = "expense_categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_expense_category_org_key"),
        Index(
            "uq_expense_category_global_key",
            "key",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_fixed_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    expenses: Mapped[list[DailyReportExpense]] = relationship(back_populates="category")

    def __repr__(self) -> str:
        return f"<ExpenseCategory {self.key}>"
