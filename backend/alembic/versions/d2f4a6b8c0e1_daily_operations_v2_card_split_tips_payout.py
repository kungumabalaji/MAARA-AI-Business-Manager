"""daily operations template v2: card till/machine split, tips, payout

Revision ID: d2f4a6b8c0e1
Revises: c1a2b3d4e5f6
Create Date: 2026-09-13

Adds a version 2 of the "daily-operations" template for Dosa n Chutney:
splits the single card_sales field into card_sales_till / card_sales_machine,
and adds two new (non-total-affecting) fields, tips_on_card and payout, to
match the business's real sales-tracker columns.

Template versions are immutable once reports are pinned to them
(daily_reports.template_version_id), so this is a new version rather than an
edit of version 1 — existing/historical reports keep resolving against v1
untouched. report_templates.current_version_id is repointed at v2 so new
Saves (and edits of reports already on v2) use the new fields.

total_sales' SUM only lists card_sales_till/card_sales_machine plus the other
channel keys — tips_on_card and payout are deliberately left out, same
treatment as opening_cash/misc_income in v1, so they don't inflate the sales
total.

Reversible: downgrade repoints current_version_id back to v1 and deletes the
v2 rows. This will fail if any daily_reports already reference v2 — those
reports must be reassigned or removed first.
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d2f4a6b8c0e1"
down_revision: str | Sequence[str] | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEMPLATE_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
VERSION_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")

SECTION_SALES_ID = uuid.uuid4()
SECTION_EXPENSES_ID = uuid.uuid4()
SECTION_SUMMARY_ID = uuid.uuid4()

report_templates = sa.table(
    "report_templates",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("current_version_id", postgresql.UUID(as_uuid=True)),
)

report_template_versions = sa.table(
    "report_template_versions",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("report_template_id", postgresql.UUID(as_uuid=True)),
    sa.column("version_number", sa.Integer),
    sa.column("status", sa.String),
    sa.column("published_at", sa.DateTime(timezone=True)),
)

report_sections = sa.table(
    "report_sections",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("template_version_id", postgresql.UUID(as_uuid=True)),
    sa.column("key", sa.String),
    sa.column("label", sa.String),
    sa.column("display_order", sa.Integer),
)

report_fields = sa.table(
    "report_fields",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("section_id", postgresql.UUID(as_uuid=True)),
    sa.column("key", sa.String),
    sa.column("label", sa.String),
    sa.column("field_type", sa.String),
    sa.column("required", sa.Boolean),
    sa.column("is_calculated", sa.Boolean),
    sa.column("display_order", sa.Integer),
)

calculation_rules = sa.table(
    "calculation_rules",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("template_version_id", postgresql.UUID(as_uuid=True)),
    sa.column("key", sa.String),
    sa.column("operation", sa.String),
    sa.column("operands", postgresql.JSONB),
)

# (key, label, required)
SALES_FIELDS = [
    ("opening_cash", "Opening Cash", False),
    ("card_sales_till", "Card Sales (Till)", False),
    ("card_sales_machine", "Card Sales (Machine)", False),
    ("cash_sales", "Cash Sales", False),
    ("uber_eats", "Uber Eats Sales", False),
    ("just_eat", "Just Eat Sales", False),
    ("deliveroo", "Deliveroo Sales", False),
    ("other_sales", "Other Sales", False),
    ("tips_on_card", "Tips on Card", False),
    ("payout", "Payout", False),
    ("misc_income", "Misc Income", False),
]

# card_sales_till is a till-recorded reconciliation figure, not revenue — the
# card machine's own reading is what actually feeds total_sales (verified
# against dosa-chutney-sales-june.csv: Total Sales = Machine + Cash + delivery
# platforms + Website/Others; Till doesn't fit that formula for any row).
SALES_CHANNEL_KEYS = ["card_sales_machine", "cash_sales", "uber_eats", "just_eat", "deliveroo", "other_sales"]


def upgrade() -> None:
    from datetime import UTC, datetime

    op.bulk_insert(
        report_template_versions,
        [
            {
                "id": VERSION_ID,
                "report_template_id": TEMPLATE_ID,
                "version_number": 2,
                "status": "published",
                "published_at": datetime.now(UTC),
            }
        ],
    )

    op.bulk_insert(
        report_sections,
        [
            {"id": SECTION_SALES_ID, "template_version_id": VERSION_ID, "key": "sales", "label": "Income / Sales", "display_order": 1},
            {"id": SECTION_EXPENSES_ID, "template_version_id": VERSION_ID, "key": "expenses", "label": "Expenses", "display_order": 2},
            {"id": SECTION_SUMMARY_ID, "template_version_id": VERSION_ID, "key": "summary", "label": "Summary", "display_order": 3},
        ],
    )

    sales_field_rows = [
        {
            "id": uuid.uuid4(),
            "section_id": SECTION_SALES_ID,
            "key": key,
            "label": label,
            "field_type": "money",
            "required": required,
            "is_calculated": False,
            "display_order": order,
        }
        for order, (key, label, required) in enumerate(SALES_FIELDS, start=1)
    ]
    sales_field_rows.append(
        {
            "id": uuid.uuid4(),
            "section_id": SECTION_SALES_ID,
            "key": "total_sales",
            "label": "Total Sales",
            "field_type": "money",
            "required": False,
            "is_calculated": True,
            "display_order": len(SALES_FIELDS) + 1,
        }
    )
    op.bulk_insert(report_fields, sales_field_rows)

    op.bulk_insert(
        report_fields,
        [
            {
                "id": uuid.uuid4(),
                "section_id": SECTION_EXPENSES_ID,
                "key": "total_expenses",
                "label": "Total Expenses",
                "field_type": "money",
                "required": False,
                "is_calculated": True,  # populated by report_service from daily_report_expenses, not a calculation_rules row
                "display_order": 1,
            },
            {
                "id": uuid.uuid4(),
                "section_id": SECTION_EXPENSES_ID,
                "key": "next_day_open_cash",
                "label": "Next-Day Open Cash",
                "field_type": "money",
                "required": False,
                "is_calculated": False,
                "display_order": 2,
            },
            {
                "id": uuid.uuid4(),
                "section_id": SECTION_EXPENSES_ID,
                "key": "cash_balance",
                "label": "Cash Balance",
                "field_type": "money",
                "required": False,
                "is_calculated": False,
                "display_order": 3,
            },
            {
                "id": uuid.uuid4(),
                "section_id": SECTION_SUMMARY_ID,
                "key": "operating_profit",
                "label": "Operating Profit",
                "field_type": "money",
                "required": False,
                "is_calculated": True,
                "display_order": 1,
            },
        ],
    )

    op.bulk_insert(
        calculation_rules,
        [
            {
                "id": uuid.uuid4(),
                "template_version_id": VERSION_ID,
                "key": "total_sales",
                "operation": "SUM",
                "operands": {"items": [{"ref": key} for key in SALES_CHANNEL_KEYS]},
            },
            {
                "id": uuid.uuid4(),
                "template_version_id": VERSION_ID,
                "key": "operating_profit",
                "operation": "SUBTRACT",
                "operands": {"left": {"ref": "total_sales"}, "right": {"ref": "total_expenses"}},
            },
        ],
    )

    op.execute(
        sa.update(report_templates)
        .where(report_templates.c.id == TEMPLATE_ID)
        .values(current_version_id=VERSION_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.update(report_templates).where(report_templates.c.id == TEMPLATE_ID).values(
            current_version_id=sa.select(report_template_versions.c.id)
            .where(
                report_template_versions.c.report_template_id == TEMPLATE_ID,
                report_template_versions.c.version_number == 1,
            )
            .scalar_subquery()
        )
    )
    op.execute(sa.delete(calculation_rules).where(calculation_rules.c.template_version_id == VERSION_ID))
    op.execute(
        sa.delete(report_fields).where(
            report_fields.c.section_id.in_([SECTION_SALES_ID, SECTION_EXPENSES_ID, SECTION_SUMMARY_ID])
        )
    )
    op.execute(
        sa.delete(report_sections).where(
            report_sections.c.id.in_([SECTION_SALES_ID, SECTION_EXPENSES_ID, SECTION_SUMMARY_ID])
        )
    )
    op.execute(sa.delete(report_template_versions).where(report_template_versions.c.id == VERSION_ID))
