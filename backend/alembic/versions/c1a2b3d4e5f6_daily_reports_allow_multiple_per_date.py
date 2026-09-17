"""daily reports: allow multiple entries per date

Revision ID: c1a2b3d4e5f6
Revises: b6827bcf3c3b
Create Date: 2026-09-08

Switches the daily report model from "one editable report per date" to
"every Save is an independent entry". Dashboards sum every report in a date
range, so repeated saves accumulate instead of overwriting.

Only change: drop the UNIQUE(report_template_id, report_date) constraint so a
second INSERT for the same date is allowed. daily_report_values keeps its own
UNIQUE(daily_report_id, field_id) — one value per field *within* a report.

Reversible: downgrade re-adds the constraint, which will fail if duplicate
(template, date) rows already exist. De-duplicate first if rolling back.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: str | Sequence[str] | None = "b6827bcf3c3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_daily_report_template_date", "daily_reports", type_="unique")
    # The index dashboards use to pull an org's reports in date order, now also
    # ordered by creation time so "latest entry for a date" is a cheap lookup.
    op.create_index(
        "ix_daily_reports_org_date_created",
        "daily_reports",
        ["organization_id", "report_date", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_daily_reports_org_date_created", table_name="daily_reports")
    op.create_unique_constraint(
        "uq_daily_report_template_date",
        "daily_reports",
        ["report_template_id", "report_date"],
    )
