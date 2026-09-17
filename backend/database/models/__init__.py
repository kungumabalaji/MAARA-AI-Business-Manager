"""Import every model here so Base.metadata is fully populated for Alembic

autogenerate, and so relationship() string annotations have something to resolve
against. Anything added to database/models/ needs a line here.
"""

from database.base import Base
from database.models.audit import AuditLog
from database.models.daily_report import DailyReport, DailyReportExpense, DailyReportValue
from database.models.expense_category import ExpenseCategory
from database.models.membership import OrganizationMember
from database.models.organization import Organization
from database.models.profile import Profile
from database.models.template import (
    CalculationRule,
    ReportField,
    ReportSection,
    ReportTemplate,
    ReportTemplateVersion,
)

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
