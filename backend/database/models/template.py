from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

TEMPLATE_VERSION_STATUSES = ("draft", "published", "archived")
FIELD_TYPES = ("money", "number", "percentage", "text", "date")
CALCULATION_OPERATIONS = (
    "SUM",
    "SUM_GROUP",
    "SUBTRACT",
    "MULTIPLY",
    "DIVIDE",
    "PERCENTAGE",
    "MIN",
    "MAX",
    "ROUND",
)


class ReportTemplate(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The stable identity of a report type (e.g. "Daily Operations Ledger").

    Points at whichever version is currently live via current_version_id; the
    versions themselves hold the actual sections/fields/rules.
    """

    __tablename__ = "report_templates"
    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_report_template_org_key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_template_versions.id", ondelete="SET NULL", use_alter=True, name="fk_template_current_version"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="report_templates")
    versions: Mapped[list["ReportTemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        foreign_keys="ReportTemplateVersion.report_template_id",
    )
    current_version: Mapped["ReportTemplateVersion | None"] = relationship(
        foreign_keys=[current_version_id], post_update=True, viewonly=False
    )

    def __repr__(self) -> str:
        return f"<ReportTemplate {self.key}>"


class ReportTemplateVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A frozen-once-published snapshot of a template's sections, fields, and rules.

    daily_reports pin this id at creation and never repoint it, so a historical
    report always renders and recalculates exactly as it did the day it was filed.
    """

    __tablename__ = "report_template_versions"
    __table_args__ = (
        UniqueConstraint("report_template_id", "version_number", name="uq_template_version_number"),
        CheckConstraint("status IN ('draft','published','archived')", name="ck_template_version_status"),
    )

    report_template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )

    template: Mapped["ReportTemplate"] = relationship(back_populates="versions", foreign_keys=[report_template_id])
    sections: Mapped[list["ReportSection"]] = relationship(
        back_populates="template_version",
        cascade="all, delete-orphan",
        order_by="ReportSection.display_order",
    )
    calculation_rules: Mapped[list["CalculationRule"]] = relationship(
        back_populates="template_version", cascade="all, delete-orphan"
    )
    daily_reports: Mapped[list["DailyReport"]] = relationship(back_populates="template_version")

    def __repr__(self) -> str:
        return f"<ReportTemplateVersion template={self.report_template_id} v{self.version_number} {self.status}>"


class ReportSection(Base, UUIDPrimaryKeyMixin):
    """A named group of fields within a template version (e.g. "sales", "expenses").

    A section's key is what calculation_rules.operands references for SUM_GROUP.
    """

    __tablename__ = "report_sections"
    __table_args__ = (UniqueConstraint("template_version_id", "key", name="uq_section_version_key"),)

    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_template_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    template_version: Mapped["ReportTemplateVersion"] = relationship(back_populates="sections")
    fields: Mapped[list["ReportField"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="ReportField.display_order"
    )

    def __repr__(self) -> str:
        return f"<ReportSection {self.key}>"


class ReportField(Base, UUIDPrimaryKeyMixin):
    """One entry line on a report. This — not a database column — is what a business's

    "Uber Eats Sales" or "POS Sales" is. field_metadata is an open extensibility hatch
    (e.g. select options) so a genuinely new need doesn't require a new column either.
    """

    __tablename__ = "report_fields"
    __table_args__ = (
        UniqueConstraint("section_id", "key", name="uq_field_section_key"),
        CheckConstraint("field_type IN ('money','number','percentage','text','date')", name="ck_field_type"),
    )

    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_sections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    field_type: Mapped[str] = mapped_column(String(20), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_calculated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    field_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    section: Mapped["ReportSection"] = relationship(back_populates="fields")
    values: Mapped[list["DailyReportValue"]] = relationship(back_populates="field")

    def __repr__(self) -> str:
        return f"<ReportField {self.key}>"


class CalculationRule(Base, UUIDPrimaryKeyMixin):
    """A configuration-driven formula. key matches the report_fields.key it populates.

    operands is validated JSON (see calculations/registry.py) — never executed as code.
    """

    __tablename__ = "calculation_rules"
    __table_args__ = (
        UniqueConstraint("template_version_id", "key", name="uq_calc_rule_version_key"),
        CheckConstraint(
            "operation IN ('SUM','SUM_GROUP','SUBTRACT','MULTIPLY','DIVIDE','PERCENTAGE','MIN','MAX','ROUND')",
            name="ck_calc_rule_operation",
        ),
    )

    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_template_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    operands: Mapped[dict] = mapped_column(JSONB, nullable=False)

    template_version: Mapped["ReportTemplateVersion"] = relationship(back_populates="calculation_rules")

    def __repr__(self) -> str:
        return f"<CalculationRule {self.key}={self.operation}>"
