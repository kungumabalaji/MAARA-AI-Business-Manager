"""initial schema

Revision ID: 3a069936839d
Revises:
Create Date: 2026-08-08 14:13:35.508060

Creates the full multi-tenant reporting schema: organizations, membership,
the dynamic report-template engine (versions/sections/fields/calculation
rules), expense categories, daily reports and their values/expenses, and
the append-only audit log.

Also creates a `profiles` row for every Supabase auth user via a trigger on
auth.users, so the app never has to create profiles itself.

gen_random_uuid() is a Postgres core builtin since v13 — no extension needed.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3a069936839d'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- profiles (mirrors auth.users) ------------------------------------
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ---- organizations ------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # ---- organization_members ------------------------------------------------
    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member_org_user"),
        sa.CheckConstraint("role IN ('owner','admin','manager','staff')", name="ck_org_member_role"),
    )
    op.create_index("ix_org_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_org_members_user_id", "organization_members", ["user_id"])

    # ---- report_templates -----------------------------------------------------
    # current_version_id's FK is added later via ALTER, once report_template_versions exists.
    op.create_table(
        "report_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "key", name="uq_report_template_org_key"),
    )
    op.create_index("ix_report_templates_organization_id", "report_templates", ["organization_id"])

    # ---- report_template_versions ----------------------------------------------
    op.create_table(
        "report_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "report_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("report_template_id", "version_number", name="uq_template_version_number"),
        sa.CheckConstraint("status IN ('draft','published','archived')", name="ck_template_version_status"),
    )
    op.create_index("ix_template_versions_template_id", "report_template_versions", ["report_template_id"])

    # now that report_template_versions exists, wire up report_templates.current_version_id
    op.create_foreign_key(
        "fk_template_current_version",
        "report_templates",
        "report_template_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ---- report_sections -----------------------------------------------------
    op.create_table(
        "report_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_template_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("template_version_id", "key", name="uq_section_version_key"),
    )
    op.create_index("ix_report_sections_template_version_id", "report_sections", ["template_version_id"])

    # ---- report_fields -----------------------------------------------------
    op.create_table(
        "report_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_sections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("field_type", sa.String(20), nullable=False),
        sa.Column("required", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_calculated", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.UniqueConstraint("section_id", "key", name="uq_field_section_key"),
        sa.CheckConstraint("field_type IN ('money','number','percentage','text','date')", name="ck_field_type"),
    )
    op.create_index("ix_report_fields_section_id", "report_fields", ["section_id"])

    # ---- calculation_rules -----------------------------------------------------
    op.create_table(
        "calculation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_template_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("operands", postgresql.JSONB, nullable=False),
        sa.UniqueConstraint("template_version_id", "key", name="uq_calc_rule_version_key"),
        sa.CheckConstraint(
            "operation IN ('SUM','SUM_GROUP','SUBTRACT','MULTIPLY','DIVIDE','PERCENTAGE','MIN','MAX','ROUND')",
            name="ck_calc_rule_operation",
        ),
    )
    op.create_index("ix_calculation_rules_template_version_id", "calculation_rules", ["template_version_id"])

    # ---- expense_categories -----------------------------------------------------
    op.create_table(
        "expense_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("is_fixed_cost", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("organization_id", "key", name="uq_expense_category_org_key"),
    )
    op.create_index("ix_expense_categories_organization_id", "expense_categories", ["organization_id"])
    # Partial unique index: system-default categories (organization_id IS NULL) must
    # also have unique keys among themselves — a plain UNIQUE constraint wouldn't
    # catch that, since Postgres treats every NULL as distinct.
    op.create_index(
        "uq_expense_category_global_key",
        "expense_categories",
        ["key"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )

    # ---- daily_reports -----------------------------------------------------
    op.create_table(
        "daily_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_templates.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "template_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_template_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("report_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "prepared_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organization_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "checked_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organization_members.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("report_template_id", "report_date", name="uq_daily_report_template_date"),
        sa.CheckConstraint("status IN ('draft','submitted','approved','rejected')", name="ck_daily_report_status"),
    )
    op.create_index("ix_daily_reports_organization_id", "daily_reports", ["organization_id"])
    op.create_index("ix_daily_reports_report_template_id", "daily_reports", ["report_template_id"])
    op.create_index("ix_daily_reports_report_date", "daily_reports", ["report_date"])
    # The index dashboards and list views actually need: an org's reports in date order.
    op.create_index("ix_daily_reports_org_date", "daily_reports", ["organization_id", "report_date"])

    # ---- daily_report_values -----------------------------------------------------
    op.create_table(
        "daily_report_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "daily_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("daily_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_fields.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("value_numeric", sa.Numeric(18, 4), nullable=True),
        sa.Column("value_text", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("daily_report_id", "field_id", name="uq_report_value_report_field"),
    )
    op.create_index("ix_daily_report_values_daily_report_id", "daily_report_values", ["daily_report_id"])
    op.create_index("ix_daily_report_values_field_id", "daily_report_values", ["field_id"])

    # ---- daily_report_expenses -----------------------------------------------------
    op.create_table(
        "daily_report_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "daily_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("daily_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "expense_category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("expense_categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.String(300), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_daily_report_expenses_daily_report_id", "daily_report_expenses", ["daily_report_id"])

    # ---- audit_logs -----------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("field_key", sa.String(80), nullable=True),
        sa.Column("old_value", postgresql.JSONB, nullable=True),
        sa.Column("new_value", postgresql.JSONB, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])

    # ---- auth.users -> public.profiles sync trigger -----------------------------
    # Standard Supabase pattern: a row appears here the instant someone signs up,
    # with no just-in-time creation logic (and no race condition) in FastAPI.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            INSERT INTO public.profiles (id, display_name)
            VALUES (NEW.id, NEW.raw_user_meta_data ->> 'display_name')
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_auth_user();")

    op.drop_table("audit_logs")
    op.drop_table("daily_report_expenses")
    op.drop_table("daily_report_values")
    op.drop_table("daily_reports")
    op.drop_index("uq_expense_category_global_key", table_name="expense_categories")
    op.drop_table("expense_categories")
    op.drop_table("calculation_rules")
    op.drop_table("report_fields")
    op.drop_table("report_sections")
    op.drop_constraint("fk_template_current_version", "report_templates", type_="foreignkey")
    op.drop_table("report_template_versions")
    op.drop_table("report_templates")
    op.drop_table("organization_members")
    op.drop_table("organizations")
    op.drop_table("profiles")
