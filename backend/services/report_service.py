"""Orchestrates a daily report save: validate raw input against the template,

sum expenses into total_expenses, run the calculation engine authoritatively,
and persist everything transactionally. This is the one place "what the user
typed" turns into "what the report actually says" — nothing upstream of this
is trusted as final.
"""

import uuid
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from calculations.errors import CalculationError
from calculations.evaluator import FieldSpec, RuleSpec, evaluate, validate_rules
from database.models import DailyReport, ReportField
from repositories import daily_report_repository, template_repository
from schemas.daily_report import DailyReportOut, DailyReportSavePayload, ExpenseOut

TEMPLATE_KEY = "daily-operations"
TOTAL_EXPENSES_FIELD_KEY = "total_expenses"
NUMERIC_FIELD_TYPES = {"money", "number", "percentage"}


def _to_decimal(raw: str) -> Decimal:
    try:
        return Decimal(raw) if raw not in (None, "") else Decimal("0")
    except InvalidOperation:
        return Decimal("0")


def _resolve_active_template_and_version(db: Session, organization_id: uuid.UUID):
    templates = template_repository.list_templates(db, organization_id)
    template = next((t for t in templates if t.key == TEMPLATE_KEY), None)
    if template is None or template.current_version_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This organization has no published daily report template yet.",
        )
    version = template_repository.get_version(db, organization_id, template.id, template.current_version_id)
    return template, version


def save_daily_report(
    db: Session,
    organization_id: uuid.UUID,
    report_date: date_type,
    payload: DailyReportSavePayload,
    actor_id: uuid.UUID,
) -> DailyReportOut:
    template, version = _resolve_active_template_and_version(db, organization_id)

    all_fields: list[ReportField] = [f for section in version.sections for f in section.fields]
    fields_by_key = {f.key: f for f in all_fields}

    raw_fields = [f for f in all_fields if not f.is_calculated]
    unknown_keys = set(payload.values) - {f.key for f in raw_fields}
    if unknown_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown field(s) for this template: {', '.join(sorted(unknown_keys))}",
        )

    report = daily_report_repository.get_or_create_draft(
        db, organization_id, template.id, version.id, report_date, created_by=actor_id
    )
    report.prepared_by = payload.prepared_by
    report.checked_by = payload.checked_by

    # ---- raw values: default every non-calculated field to 0/empty, never leave gaps ----
    engine_raw_values: dict[str, Decimal] = {}
    values_by_field_id: dict[uuid.UUID, dict] = {}

    for field in raw_fields:
        submitted = payload.values.get(field.key, "")
        if field.field_type in NUMERIC_FIELD_TYPES:
            amount = _to_decimal(submitted)
            values_by_field_id[field.id] = {"value_numeric": amount, "value_text": None}
            engine_raw_values[field.key] = amount
        else:
            values_by_field_id[field.id] = {"value_numeric": None, "value_text": submitted or None}

    # ---- expenses: this form only ever produces ad-hoc rows (no category picker yet) ----
    expense_rows = [
        {
            "description": e.description,
            "amount": e.amount,
            "expense_category_id": e.expense_category_id,
            "notes": e.notes,
        }
        for e in payload.expenses
        if e.description.strip() and e.amount != 0
    ]
    daily_report_repository.replace_expenses(db, report, expense_rows)
    total_expenses = sum((row["amount"] for row in expense_rows), Decimal("0"))

    if TOTAL_EXPENSES_FIELD_KEY in fields_by_key:
        engine_raw_values[TOTAL_EXPENSES_FIELD_KEY] = total_expenses

    # ---- run the calculation engine authoritatively ----
    engine_fields = [FieldSpec(key=f.key, section_key=f.section.key, is_calculated=f.is_calculated) for f in all_fields]
    engine_rules = [RuleSpec(key=r.key, operation=r.operation, operands=r.operands) for r in version.calculation_rules]

    try:
        ordered_rules = validate_rules(engine_fields, engine_rules)
        computed = evaluate(engine_fields, ordered_rules, engine_raw_values)
    except CalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # total_expenses itself has no calculation_rule (it's summed above, not engine-derived) —
    # make sure it lands in the persisted/returned values even though evaluate() never touched it.
    computed.setdefault(TOTAL_EXPENSES_FIELD_KEY, total_expenses)

    for field in all_fields:
        if field.is_calculated:
            values_by_field_id[field.id] = {"value_numeric": computed.get(field.key, Decimal("0")), "value_text": None}

    daily_report_repository.upsert_values(db, report, values_by_field_id)
    report.status = "submitted"

    db.commit()
    db.refresh(report)

    return _to_out(report, fields_by_key)


def get_daily_report(db: Session, organization_id: uuid.UUID, report_date: date_type) -> DailyReportOut | None:
    template, _version = _resolve_active_template_and_version(db, organization_id)
    report = daily_report_repository.get_by_date(db, organization_id, template.id, report_date)
    if report is None:
        return None

    version = template_repository.get_version(db, organization_id, template.id, report.template_version_id)
    fields_by_key = {f.key: f for section in version.sections for f in section.fields}
    return _to_out(report, fields_by_key)


def _to_out(report: DailyReport, fields_by_key: dict[str, ReportField]) -> DailyReportOut:
    field_by_id = {f.id: f for f in fields_by_key.values()}
    values: dict[str, str] = {}
    for v in report.values:
        field = field_by_id.get(v.field_id)
        if field is None:
            continue
        values[field.key] = str(v.value_numeric) if v.value_numeric is not None else (v.value_text or "")

    return DailyReportOut(
        id=report.id,
        organization_id=report.organization_id,
        report_date=report.report_date,
        status=report.status,
        values=values,
        expenses=[ExpenseOut.model_validate(e) for e in report.expenses],
        prepared_by=report.prepared_by,
        checked_by=report.checked_by,
    )
