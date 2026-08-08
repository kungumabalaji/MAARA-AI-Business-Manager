"""Import every model here so Base.metadata is fully populated for Alembic

autogenerate, and so relationship() string annotations have something to resolve
against. Anything added to database/models/ needs a line here.
"""

from database.base import Base
from database.models.profile import Profile
from database.models.organization import Organization
from database.models.membership import OrganizationMember
from database.models.template import (
    ReportTemplate,
    ReportTemplateVersion,
    ReportSection,
    ReportField,
    CalculationRule,
)
from database.models.expense_category import ExpenseCategory
from database.models.daily_report import DailyReport, DailyReportValue, DailyReportExpense
from database.models.audit import AuditLog

__all__ = [
    "Base",
    "Profile",
    "Organization",
    "OrganizationMember",
    "ReportTemplate",
    "ReportTemplateVersion",
    "ReportSection",
    "ReportField",
    "CalculationRule",
    "ExpenseCategory",
    "DailyReport",
    "DailyReportValue",
    "DailyReportExpense",
    "AuditLog",
]
