"""Read-side aggregation over real daily_reports data. Computed on read via

straightforward SQL grouping — no precomputed aggregate tables. At this data
volume (a handful of rows per org per day) that's fast; see the architecture
doc §15 for when that stops being true and what to do about it then.
"""

import calendar
import uuid
from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from database.models import DailyReport, DailyReportExpense, DailyReportValue, ExpenseCategory, ReportField

# card_sales_till is a reconciliation reading, not revenue — Total Sales is
# built from the card machine's own figure (verified against the source CSV:
# Machine + Cash + delivery platforms + Website/Others matches Total Sales on
# every row; Till doesn't).
SALES_CHANNEL_KEYS = ["cardSalesMachine", "cashSales", "uberEatsSales", "justEatSales", "deliverooSales", "otherSales"]
# Reported alongside the channel keys but not part of the sales total — tips
# and payout are cash-handling/reconciliation figures, not revenue.
SALES_EXTRA_KEYS = ["tips", "payout"]
FIELD_KEY_TO_CHANNEL = {
    # Pre-v2 reports only have one combined "card_sales" field, which fed
    # v1's total_sales the same way the machine reading feeds v2's — map it
    # there so historical totals keep counting instead of disappearing.
    "card_sales": "cardSalesMachine",
    "card_sales_machine": "cardSalesMachine",
    "cash_sales": "cashSales",
    "uber_eats": "uberEatsSales",
    "just_eat": "justEatSales",
    "deliveroo": "deliverooSales",
    "other_sales": "otherSales",
    "tips_on_card": "tips",
    "payout": "payout",
    "misc_income": "miscIncome",
    "opening_cash": "openingCash",
    "total_sales": "totalSales",
    "total_expenses": "totalExpenses",
    "operating_profit": "operatingProfit",
    "next_day_open_cash": "nextDayOpenCash",
    "cash_balance": "cashBalance",
}


def _load_reports_with_values(
    db: Session, organization_id: uuid.UUID, since: date_type, until: date_type | None = None
) -> list[DailyReport]:
    """Every report in [since, until] for the org — including multiple reports
    that share the same date. Callers aggregate; nothing here dedupes by date.
    """
    stmt = (
        select(DailyReport)
        .where(DailyReport.organization_id == organization_id, DailyReport.report_date >= since)
        .options(
            selectinload(DailyReport.values).selectinload(DailyReportValue.field),
            selectinload(DailyReport.expenses),
        )
        .order_by(DailyReport.report_date)
    )
    if until is not None:
        stmt = stmt.where(DailyReport.report_date <= until)
    return list(db.execute(stmt).scalars())


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

    # Every Save is its own report, so multiple rows can share a date — sum them
    # into one row per date so a day's figure is the day's total.
    keys = [*SALES_CHANNEL_KEYS, *SALES_EXTRA_KEYS, "miscIncome"]
    by_date: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for r in reports:
        values = _row_values(r)
        bucket = by_date[r.report_date.isoformat()]
        for k in keys:
            bucket[k] += values.get(k, Decimal("0"))

    return [{"date": d, **{k: str(by_date[d].get(k, Decimal("0"))) for k in keys}} for d in sorted(by_date)]


def expenses_daily(db: Session, organization_id: uuid.UUID, days: int) -> list[dict]:
    """One row per date: the summed expense total across every report that day."""
    since = date_type.today() - timedelta(days=days)
    reports = _load_reports_with_values(db, organization_id, since)

    by_date: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in reports:
        by_date[r.report_date.isoformat()] += sum((e.amount for e in r.expenses), Decimal("0"))

    return [{"date": d, "total": str(by_date[d])} for d in sorted(by_date)]


def sales_monthly(db: Session, organization_id: uuid.UUID, months: int) -> list[dict]:
    since = date_type.today().replace(day=1) - timedelta(days=31 * months)
    reports = _load_reports_with_values(db, organization_id, since)

    by_month: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for r in reports:
        month_key = r.report_date.strftime("%Y-%m")
        values = _row_values(r)
        for k in [*SALES_CHANNEL_KEYS, *SALES_EXTRA_KEYS, "miscIncome"]:
            by_month[month_key][k] += values.get(k, Decimal("0"))

    return [
        {"month": month, **{k: str(v) for k, v in totals.items()}}
        for month, totals in sorted(by_month.items())
    ]


def sales_month_summary(db: Session, organization_id: uuid.UUID, year: int, month: int) -> dict:
    """The four Sales Dashboard KPIs for exactly one calendar month — grouped
    strictly by report_date within [year-month-01, year-month-last_day].

    avgDailySales divides by the number of calendar days in the month, not by
    how many of those days have a saved entry — a sparsely-filled month must
    not look like a high-average month.
    """
    days_in_month = calendar.monthrange(year, month)[1]
    since = date_type(year, month, 1)
    until = date_type(year, month, days_in_month)
    reports = _load_reports_with_values(db, organization_id, since, until)

    # Every Save is its own report, so multiple rows can share a date — sum
    # them into one row per date first, same as sales_daily/sales_monthly.
    by_date: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for r in reports:
        values = _row_values(r)
        bucket = by_date[r.report_date.isoformat()]
        for k in [*SALES_CHANNEL_KEYS, *SALES_EXTRA_KEYS]:
            bucket[k] += values.get(k, Decimal("0"))

    total_sales = Decimal("0")
    card_tips = Decimal("0")
    best_date: str | None = None
    best_total = Decimal("-1")

    for d, bucket in by_date.items():
        day_total = sum((bucket.get(k, Decimal("0")) for k in SALES_CHANNEL_KEYS), Decimal("0"))
        total_sales += day_total
        card_tips += bucket.get("tips", Decimal("0"))
        if day_total > best_total:
            best_total = day_total
            best_date = d

    avg_daily_sales = (total_sales / days_in_month).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    best_day = None
    if best_date is not None:
        parsed = date_type.fromisoformat(best_date)
        best_day = {"date": best_date, "weekday": parsed.strftime("%A"), "sales": str(best_total)}

    return {
        "year": year,
        "month": calendar.month_name[month],
        "daysInMonth": days_in_month,
        "totalSales": str(total_sales),
        "avgDailySales": str(avg_daily_sales),
        "bestDay": best_day,
        "cardTips": str(card_tips),
    }


def list_expense_categories(db: Session, organization_id: uuid.UUID) -> list[dict]:
    """Every category available to this org — its own custom additions plus the
    system defaults (organization_id IS NULL) — regardless of whether any
    expense has actually been recorded against it yet.
    """
    categories = db.execute(
        select(ExpenseCategory)
        .where(or_(ExpenseCategory.organization_id == organization_id, ExpenseCategory.organization_id.is_(None)))
        .order_by(ExpenseCategory.display_order, ExpenseCategory.label)
    ).scalars().all()
    return [
        {"key": c.key, "label": c.label, "is_fixed_cost": c.is_fixed_cost, "is_custom": c.organization_id is not None}
        for c in categories
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


def expenses_recent(
    db: Session,
    organization_id: uuid.UUID,
    limit: int,
    since: date_type | None = None,
    until: date_type | None = None,
) -> list[dict]:
    window_start = since if since is not None else date_type.today() - timedelta(days=180)
    reports = _load_reports_with_values(db, organization_id, window_start, until)
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

    day_reports = [
        r for r in _load_reports_with_values(db, organization_id, report_date) if r.report_date == report_date
    ]
    if not day_reports:
        return None

    # Multiple Saves for the day are independent entries — sum the additive
    # figures across all of them.
    def _sum(key: str) -> Decimal:
        return sum((_row_values(r).get(key, Decimal("0")) for r in day_reports), Decimal("0"))

    revenue = _sum("totalSales") + _sum("miscIncome")
    expenses = _sum("totalExpenses")
    profit = revenue - expenses

    expected_cash = _sum("openingCash") + _sum("cashSales") - expenses
    actual_cash = _sum("cashBalance")
    variance = actual_cash - expected_cash
    values = {"cashBalance": actual_cash}

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
