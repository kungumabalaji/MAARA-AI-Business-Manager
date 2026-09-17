from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

DAILY_REPORT_STATUSES = ("draft", "submitted", "approved", "rejected")


class DailyReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One filed report for one organization on one date, pinned to the exact

    template version used so it stays reproducible even after the template changes.
    See the architecture doc §11 for why created_by / prepared_by / checked_by /
    approved_by are four distinct, non-redundant fields.
    """

    __tablename__ = "daily_reports"
    # No unique constraint on (template, date): every Save creates an independent
    # entry and dashboards sum them (see migration c1a2b3d4e5f6). Multiple reports
    # per date are expected.
    __table_args__ = (
        CheckConstraint("status IN ('draft','submitted','approved','rejected')", name="ck_daily_report_status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_templates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_template_versions.id", ondelete="RESTRICT"), nullable=False
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    prepared_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True
    )
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    template_version: Mapped[ReportTemplateVersion] = relationship(back_populates="daily_reports")
    values: Mapped[list[DailyReportValue]] = relationship(
        back_populates="daily_report", cascade="all, delete-orphan"
    )
    expenses: Mapped[list[DailyReportExpense]] = relationship(
        back_populates="daily_report", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DailyReport org={self.organization_id} date={self.report_date} status={self.status}>"


class DailyReportValue(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """One answered field on a report — raw user input or an authoritative calculated

    output, distinguished via report_fields.is_calculated. value_numeric covers
    money/number/percentage; value_text covers text/date fields.
    """

    __tablename__ = "daily_report_values"
    __table_args__ = (UniqueConstraint("daily_report_id", "field_id", name="uq_report_value_report_field"),)

    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_fields.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    daily_report: Mapped[DailyReport] = relationship(back_populates="values")
    field: Mapped[ReportField] = relationship(back_populates="values")

    def __repr__(self) -> str:
        return f"<DailyReportValue report={self.daily_report_id} field={self.field_id}>"


class DailyReportExpense(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A line in the expense list. expense_category_id NULL = ad-hoc, user-typed row."""

    __tablename__ = "daily_report_expenses"

    daily_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expense_category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    daily_report: Mapped[DailyReport] = relationship(back_populates="expenses")
    category: Mapped[ExpenseCategory | None] = relationship(back_populates="expenses")

    def __repr__(self) -> str:
        return f"<DailyReportExpense {self.description} {self.amount}>"
