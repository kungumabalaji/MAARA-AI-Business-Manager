"""Read-side aggregation over real daily_reports data. Computed on read via

straightforward SQL grouping — no precomputed aggregate tables. At this data
volume (a handful of rows per org per day) that's fast; see the architecture
doc §15 for when that stops being true and what to do about it then.
"""

import uuid
from collections import defaultdict
from datetime import date as date_type, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import DailyReport, DailyReportExpense, DailyReportValue, ExpenseCategory, ReportField

SALES_CHANNEL_KEYS = ["cardSales", "cashSales", "uberEatsSales", "justEatSales", "deliverooSales", "otherSales"]
FIELD_KEY_TO_CHANNEL = {
    "card_sales": "cardSales",
    "cash_sales": "cashSales",
    "uber_eats": "uberEatsSales",
    "just_eat": "justEatSales",
    "deliveroo": "deliverooSales",
    "other_sales": "otherSales",
    "misc_income": "miscIncome",
    "opening_cash": "openingCash",
    "total_sales": "totalSales",
    "total_expenses": "totalExpenses",
    "operating_profit": "operatingProfit",
    "next_day_open_cash": "nextDayOpenCash",
    "cash_balance": "cashBalance",
}


def _load_reports_with_values(db: Session, organization_id: uuid.UUID, since: date_type) -> list[DailyReport]:
    return list(
        db.execute(
            select(DailyReport)
            .where(DailyReport.organization_id == organization_id, DailyReport.report_date >= since)
            .options(
                selectinload(DailyReport.values).selectinload(DailyReportValue.field),
                selectinload(DailyReport.expenses),
            )
            .order_by(DailyReport.report_date)
        ).scalars()
    )


def _row_values(report: DailyReport) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for v in report.values:
        field: ReportField = v.field
        key = FIELD_KEY_TO_CHANNEL.get(field.key, field.key)
        out[key] = v.value_numeric if v.value_numeric is not None else Decimal("0")
    return out


def sales_daily(db: Session, organization_id: uuid.UUID, days: int) -> list[dict]:
    since = date_type.today() - timedelta(days=days)
    reports = _load_reports_with_values(db, organization_id, since)
    return [{"date": r.report_date.isoformat(), **{k: str(_row_values(r).get(k, Decimal("0"))) for k in [*SALES_CHANNEL_KEYS, "miscIncome"]}} for r in reports]


def sales_monthly(db: Session, organization_id: uuid.UUID, months: int) -> list[dict]:
    since = date_type.today().replace(day=1) - timedelta(days=31 * months)
    reports = _load_reports_with_values(db, organization_id, since)

    by_month: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for r in reports:
        month_key = r.report_date.strftime("%Y-%m")
        values = _row_values(r)
        for k in [*SALES_CHANNEL_KEYS, "miscIncome"]:
            by_month[month_key][k] += values.get(k, Decimal("0"))

    return [
        {"month": month, **{k: str(v) for k, v in totals.items()}}
        for month, totals in sorted(by_month.items())
    ]


def _category_label(db: Session, organization_id: uuid.UUID, expense: DailyReportExpense) -> str:
    if expense.expense_category_id is not None:
        category = db.get(ExpenseCategory, expense.expense_category_id)
        if category is not None:
            return category.label
    return expense.description.strip() or "Other"


def expenses_monthly(db: Session, organization_id: uuid.UUID, months: int) -> list[dict]:
    since = date_type.today().replace(day=1) - timedelta(days=31 * months)
    reports = _load_reports_with_values(db, organization_id, since)

    by_month: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in reports:
        month_key = r.report_date.strftime("%Y-%m")
        by_month[month_key] += sum((e.amount for e in r.expenses), Decimal("0"))

    return [{"month": month, "total": str(total)} for month, total in sorted(by_month.items())]


def expenses_by_category(db: Session, organization_id: uuid.UUID, since: date_type, until: date_type) -> list[dict]:
    reports = _load_reports_with_values(db, organization_id, since)
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in reports:
        if r.report_date > until:
            continue
        for e in r.expenses:
            totals[_category_label(db, organization_id, e)] += e.amount

    return sorted(
        ({"category": label, "total": str(total)} for label, total in totals.items()),
        key=lambda row: Decimal(row["total"]),
        reverse=True,
    )


def expenses_recent(db: Session, organization_id: uuid.UUID, limit: int) -> list[dict]:
    since = date_type.today() - timedelta(days=180)
    reports = _load_reports_with_values(db, organization_id, since)
    rows = [
        {
            "date": r.report_date.isoformat(),
            "description": e.description,
            "category": _category_label(db, organization_id, e),
            "amount": str(e.amount),
        }
        for r in reversed(reports)
        for e in sorted(r.expenses, key=lambda x: x.display_order)
    ]
    return rows[:limit]


def profit_monthly(db: Session, organization_id: uuid.UUID, months: int) -> list[dict]:
    since = date_type.today().replace(day=1) - timedelta(days=31 * months)
    reports = _load_reports_with_values(db, organization_id, since)

    by_month: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"revenue": Decimal("0"), "expenses": Decimal("0")})
    for r in reports:
        month_key = r.report_date.strftime("%Y-%m")
        values = _row_values(r)
        by_month[month_key]["revenue"] += values.get("totalSales", Decimal("0")) + values.get("miscIncome", Decimal("0"))
        by_month[month_key]["expenses"] += values.get("totalExpenses", Decimal("0"))

    out = []
    for month, totals in sorted(by_month.items()):
        profit = totals["revenue"] - totals["expenses"]
        out.append({"month": month, "revenue": str(totals["revenue"]), "expenses": str(totals["expenses"]), "profit": str(profit)})
    return out


def daily_summary(db: Session, organization_id: uuid.UUID, report_date: date_type | None) -> dict | None:
    """Daily P/L + Expected vs Actual Cash for one day — the most recent report

    if no date is given. Expected cash assumes expenses were paid out of the
    till in cash (opening cash + cash sales - total expenses); Actual cash is
    whatever the preparer counted and typed into Cash Balance. This is a
    simplification — without a payment-method flag per expense, it's the best
    estimate available, not a certainty.
    """
    if report_date is None:
        latest = db.execute(
            select(DailyReport)
            .where(DailyReport.organization_id == organization_id)
            .order_by(DailyReport.report_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest is None:
            return None
        report_date = latest.report_date

    reports = _load_reports_with_values(db, organization_id, report_date)
    report = next((r for r in reports if r.report_date == report_date), None)
    if report is None:
        return None

    values = _row_values(report)
    revenue = values.get("totalSales", Decimal("0")) + values.get("miscIncome", Decimal("0"))
    expenses = values.get("totalExpenses", Decimal("0"))
    profit = revenue - expenses

    expected_cash = values.get("openingCash", Decimal("0")) + values.get("cashSales", Decimal("0")) - expenses
    actual_cash = values.get("cashBalance", Decimal("0"))
    variance = actual_cash - expected_cash

    return {
        "date": report_date.isoformat(),
        "revenue": str(revenue),
        "expenses": str(expenses),
        "profit": str(profit),
        "expectedCash": str(expected_cash),
        "actualCash": str(actual_cash),
        "cashVariance": str(variance),
        "hasActualCash": "cashBalance" in values and values["cashBalance"] != 0,
    }
