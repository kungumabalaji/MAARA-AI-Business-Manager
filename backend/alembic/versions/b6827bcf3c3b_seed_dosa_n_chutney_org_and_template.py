"""seed dosa n chutney org and template

Revision ID: b6827bcf3c3b
Revises: 6a5356d68eec
Create Date: 2026-08-08 15:05:00.000000

Creates the "Dosa n Chutney" organization and its Daily Operations Ledger
template as a published version 1 — proof the generic engine reproduces the
pilot business's current UI exactly, with zero business-specific columns
anywhere in the schema. Also seeds their own custom expense categories
(Groceries, Cash & Carry, delivery commissions, ...) on top of the universal
system defaults from the previous migration.

No organization_members row is created here — there's no real Supabase auth
user yet to attach as owner. See scripts/grant_org_owner.py for that step,
run once after the first real person signs up.
"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b6827bcf3c3b'
down_revision: Union[str, Sequence[str], None] = '6a5356d68eec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORGANIZATION_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
TEMPLATE_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")
VERSION_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")

SECTION_SALES_ID = uuid.uuid4()
SECTION_EXPENSES_ID = uuid.uuid4()
SECTION_SUMMARY_ID = uuid.uuid4()

organizations = sa.table(
    "organizations",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("currency", sa.String),
)

report_templates = sa.table(
    "report_templates",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("organization_id", postgresql.UUID(as_uuid=True)),
    sa.column("key", sa.String),
    sa.column("name", sa.String),
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

expense_categories = sa.table(
    "expense_categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("organization_id", postgresql.UUID(as_uuid=True)),
    sa.column("key", sa.String),
    sa.column("label", sa.String),
    sa.column("is_fixed_cost", sa.Boolean),
    sa.column("display_order", sa.Integer),
)

# (key, label, required)
SALES_FIELDS = [
    ("opening_cash", "Opening Cash", False),
    ("card_sales", "Card Sales", False),
    ("cash_sales", "Cash Sales", False),
    ("uber_eats", "Uber Eats Sales", False),
    ("just_eat", "Just Eat Sales", False),
    ("deliveroo", "Deliveroo Sales", False),
    ("other_sales", "Other Sales", False),
    ("misc_income", "Misc Income", False),
]

SALES_CHANNEL_KEYS = ["card_sales", "cash_sales", "uber_eats", "just_eat", "deliveroo", "other_sales"]

# Dosa n Chutney's own categories, layered on top of the universal system
# defaults seeded in the previous migration.
DOSA_EXPENSE_CATEGORIES = [
    ("scottish_power", "Scottish Power (Gas & Electric)", True),
    ("groceries", "Groceries", False),
    ("cash_and_carry", "Cash & Carry", False),
    ("beer_purchases", "Beer Purchases", False),
    ("meat_bills", "Meat Bills", False),
    ("frozen_food_bills", "Frozen Food Bills", False),
    ("biffa_waste", "Biffa Waste", False),
    ("deliveroo_commission", "Deliveroo Commission", False),
    ("just_eat_commission", "Just Eat Commission", False),
    ("uber_eats_commission", "Uber Eats Commission", False),
]


def upgrade() -> None:
    op.bulk_insert(
        organizations,
        [{"id": ORGANIZATION_ID, "name": "Dosa n Chutney", "slug": "dosa-n-chutney", "currency": "GBP"}],
    )

    op.bulk_insert(
        report_templates,
        [
            {
                "id": TEMPLATE_ID,
                "organization_id": ORGANIZATION_ID,
                "key": "daily-operations",
                "name": "Daily Operations Ledger",
                "current_version_id": None,
            }
        ],
    )

    op.bulk_insert(
        report_template_versions,
        [
            {
                "id": VERSION_ID,
                "report_template_id": TEMPLATE_ID,
                "version_number": 1,
                "status": "published",
                "published_at": datetime.now(timezone.utc),
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
    total_sales_field_id = uuid.uuid4()
    sales_field_rows.append(
        {
            "id": total_sales_field_id,
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

    op.bulk_insert(
        expense_categories,
        [
            {
                "id": uuid.uuid4(),
                "organization_id": ORGANIZATION_ID,
                "key": key,
                "label": label,
                "is_fixed_cost": is_fixed_cost,
                "display_order": order,
            }
            for order, (key, label, is_fixed_cost) in enumerate(DOSA_EXPENSE_CATEGORIES, start=1)
        ],
    )


def downgrade() -> None:
    op.execute(sa.delete(expense_categories).where(expense_categories.c.organization_id == ORGANIZATION_ID))
    op.execute(
        sa.update(report_templates).where(report_templates.c.id == TEMPLATE_ID).values(current_version_id=None)
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
    op.execute(sa.delete(report_templates).where(report_templates.c.id == TEMPLATE_ID))
    op.execute(sa.delete(organizations).where(organizations.c.id == ORGANIZATION_ID))
