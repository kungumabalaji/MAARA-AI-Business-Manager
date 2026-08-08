"""seed default expense categories

Revision ID: 58a177b1c0cd
Revises: 3a069936839d
Create Date: 2026-08-08 14:15:53.901574

System-default expense categories (organization_id IS NULL), visible to every
organization regardless of vertical — deliberately generic (Rent, Utilities,
Staff Wages, ...), not food-business-specific. Dosa n Chutney's own categories
(Groceries, Cash & Carry, Meat Bills, delivery commissions, ...) are seeded as
that org's custom additions in the Phase 3 template migration, not here.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '58a177b1c0cd'
down_revision: Union[str, Sequence[str], None] = '3a069936839d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

expense_categories = sa.table(
    "expense_categories",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("organization_id", postgresql.UUID(as_uuid=True)),
    sa.column("key", sa.String),
    sa.column("label", sa.String),
    sa.column("is_fixed_cost", sa.Boolean),
    sa.column("display_order", sa.Integer),
)

# (key, label, is_fixed_cost) — universal across business types on purpose.
DEFAULT_CATEGORIES = [
    ("rent", "Rent", True),
    ("council_tax_or_rates", "Council Tax / Business Rates", True),
    ("utilities", "Utilities (Gas / Electric / Water)", True),
    ("internet_and_phone", "Internet & Phone", True),
    ("insurance", "Insurance", True),
    ("accountant_fees", "Accountant / Professional Fees", True),
    ("staff_wages", "Staff Wages", False),
    ("stock_purchases", "Stock / Supplies Purchases", False),
    ("marketing", "Marketing", False),
    ("bank_and_card_fees", "Bank & Card Processing Fees", False),
    ("travel", "Travel", False),
    ("everyday_spending", "Everyday Spending", False),
    ("other", "Other", False),
]


def upgrade() -> None:
    op.bulk_insert(
        expense_categories,
        [
            {
                "organization_id": None,
                "key": key,
                "label": label,
                "is_fixed_cost": is_fixed_cost,
                "display_order": order,
            }
            for order, (key, label, is_fixed_cost) in enumerate(DEFAULT_CATEGORIES, start=1)
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.delete(expense_categories).where(expense_categories.c.organization_id.is_(None))
    )
