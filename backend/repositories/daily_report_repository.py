import uuid
from datetime import date as date_type

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import DailyReport, DailyReportExpense, DailyReportValue


def get_by_date(
    db: Session, organization_id: uuid.UUID, report_template_id: uuid.UUID, report_date: date_type
) -> DailyReport | None:
    return db.execute(
        select(DailyReport)
        .where(
            DailyReport.organization_id == organization_id,
            DailyReport.report_template_id == report_template_id,
            DailyReport.report_date == report_date,
        )
        .options(
            selectinload(DailyReport.values),
            selectinload(DailyReport.expenses),
        )
    ).scalar_one_or_none()


def get_or_create_draft(
    db: Session,
    organization_id: uuid.UUID,
    report_template_id: uuid.UUID,
    template_version_id: uuid.UUID,
    report_date: date_type,
    created_by: uuid.UUID,
) -> DailyReport:
    existing = get_by_date(db, organization_id, report_template_id, report_date)
    if existing is not None:
        return existing

    report = DailyReport(
        organization_id=organization_id,
        report_template_id=report_template_id,
        template_version_id=template_version_id,
        report_date=report_date,
        status="draft",
        created_by=created_by,
    )
    db.add(report)
    db.flush()
    return report


def replace_expenses(db: Session, report: DailyReport, rows: list[dict]) -> None:
    for existing in list(report.expenses):
        db.delete(existing)
    db.flush()

    for order, row in enumerate(rows):
        db.add(
            DailyReportExpense(
                daily_report_id=report.id,
                expense_category_id=row.get("expense_category_id"),
                description=row["description"],
                amount=row["amount"],
                notes=row.get("notes"),
                display_order=order,
            )
        )


def upsert_values(db: Session, report: DailyReport, values_by_field_id: dict[uuid.UUID, dict]) -> None:
    """values_by_field_id: {field_id: {"value_numeric": Decimal|None, "value_text": str|None}}."""
    existing_by_field = {v.field_id: v for v in report.values}

    for field_id, payload in values_by_field_id.items():
        row = existing_by_field.get(field_id)
        if row is None:
            row = DailyReportValue(daily_report_id=report.id, field_id=field_id)
            db.add(row)
        row.value_numeric = payload.get("value_numeric")
        row.value_text = payload.get("value_text")
