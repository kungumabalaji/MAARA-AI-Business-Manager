import uuid
from datetime import date as date_type

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database.models import DailyReport, DailyReportExpense, DailyReportValue


def get_by_id(db: Session, organization_id: uuid.UUID, report_id: uuid.UUID) -> DailyReport | None:
    """Org-scoped fetch of one specific report, for the edit/delete flows."""
    return db.execute(
        select(DailyReport)
        .where(DailyReport.id == report_id, DailyReport.organization_id == organization_id)
        .options(
            selectinload(DailyReport.values),
            selectinload(DailyReport.expenses),
        )
    ).scalars().first()


def list_reports(
    db: Session,
    organization_id: uuid.UUID,
    since: date_type | None,
    until: date_type | None,
    limit: int,
    offset: int,
) -> tuple[list[DailyReport], int]:
    """Paginated reports for the records table, newest first. Returns (page, total)."""
    filters = [DailyReport.organization_id == organization_id]
    if since is not None:
        filters.append(DailyReport.report_date >= since)
    if until is not None:
        filters.append(DailyReport.report_date <= until)

    total = db.execute(select(func.count()).select_from(DailyReport).where(*filters)).scalar_one()

    rows = db.execute(
        select(DailyReport)
        .where(*filters)
        .options(
            selectinload(DailyReport.values),
            selectinload(DailyReport.expenses),
        )
        .order_by(DailyReport.report_date.desc(), DailyReport.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()

    return list(rows), total


def delete_report(db: Session, report: DailyReport) -> None:
    """Hard delete — cascades to values/expenses via the ORM relationship config."""
    db.delete(report)
    db.flush()


def get_by_date(
    db: Session, organization_id: uuid.UUID, report_template_id: uuid.UUID, report_date: date_type
) -> DailyReport | None:
    """The MOST RECENT report saved for this date. Since every Save now creates
    a new entry, several rows can share a (template, date); this returns the
    latest by creation time so "load what's there" shows the last submission.
    """
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
        .order_by(DailyReport.created_at.desc())
        .limit(1)
    ).scalars().first()


def create_report(
    db: Session,
    organization_id: uuid.UUID,
    report_template_id: uuid.UUID,
    template_version_id: uuid.UUID,
    report_date: date_type,
    created_by: uuid.UUID,
) -> DailyReport:
    """Always inserts a fresh report — repeated saves for the same date are
    independent entries, never an in-place edit.
    """
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
