"""Import the annual category x month expense tracker (one row per category,
one column per month) into MAARA via the normal save_daily_report() path.

Each category's monthly figure becomes one expense line on a report dated the
1st of that month (there's no daily grain in this source — a whole month's
category cost is one number). All of a month's categories are bundled into a
single report so a month only ever adds one extra row per date, alongside
whatever daily sales report already exists for the 1st (dashboards sum every
report for a date, so this never overwrites the day's sales figures).

Usage:
    python scripts/import_annual_expenses.py --file "C:\\Users\\Admin\\Downloads\\Dosa_n_Chutney_Annual_Expense_Tracker (2).xlsx"
    python scripts/import_annual_expenses.py --file tracker.xlsx --dry-run
"""
from __future__ import annotations

import argparse
import sys
from datetime import date as date_type
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.connection import SessionLocal  # noqa: E402
from database.models import DailyReport, ExpenseCategory, Organization, OrganizationMember  # noqa: E402
from schemas.daily_report import DailyReportSavePayload, ExpenseIn  # noqa: E402
from services.report_service import save_daily_report  # noqa: E402

MONTH_COLUMNS = [
    "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
    "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER",
]

# Excel row label -> expense_categories.key. Every key here already exists
# (either as this org's own custom category or a system default) — see
# alembic/versions/58a177b1c0cd_* and b6827bcf3c3b_*.
CATEGORY_KEY_MAP = {
    "Scottish Power (Gas & Electric)": "scottish_power",
    "Groceries": "groceries",
    "Cash & Carry": "cash_and_carry",
    "Beer Purchases": "beer_purchases",
    "Meat Bills": "meat_bills",
    "Frozen Food Bills": "frozen_food_bills",
    "Biffa Waste": "biffa_waste",
    "Internet & Phone": "internet_and_phone",
    "Marketing": "marketing",
    "Accountant Fees": "accountant_fees",
    "Deliveroo Commission": "deliveroo_commission",
    "Just Eat Commission": "just_eat_commission",
    "Uber Eats Commission": "uber_eats_commission",
    "Everyday Spending": "everyday_spending",
    "Rent": "rent",
    "Council Tax": "council_tax_or_rates",
    "Staff Wages": "staff_wages",
    "water bills": "utilities",
}


def money(value) -> Decimal:
    if pd.isna(value):
        return Decimal("0")
    text = str(value).strip().replace("£", "").replace(",", "")
    if text == "":
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Path to the annual expense tracker .xlsx")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first sheet)")
    parser.add_argument("--org-slug", default="dosa-n-chutney")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("\n==================================")
    print("MAARA ANNUAL EXPENSE IMPORT")
    print("==================================")
    print(f"\nReading: {args.file}")
    if not args.file.exists():
        raise FileNotFoundError(f"File does not exist:\n{args.file}")

    df = pd.read_excel(args.file, sheet_name=args.sheet)
    df = df.dropna(subset=["CATEGORY"])

    db = SessionLocal()
    try:
        organization = db.execute(select(Organization).where(Organization.slug == args.org_slug)).scalar_one_or_none()
        if organization is None:
            raise RuntimeError(f"Organization '{args.org_slug}' was not found.")
        print(f"Organization: {organization.name} ({organization.id})")

        member = db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization.id)
            .order_by(OrganizationMember.created_at)
        ).scalars().first()
        if member is None:
            raise RuntimeError("No organization member exists. Create/login with your MAARA user first.")
        actor_id = member.user_id

        categories = db.execute(
            select(ExpenseCategory).where(
                or_(ExpenseCategory.organization_id == organization.id, ExpenseCategory.organization_id.is_(None))
            )
        ).scalars().all()
        category_by_key = {c.key: c for c in categories}

        unmapped_labels = sorted(
            {str(r["CATEGORY"]).strip() for _, r in df.iterrows()} - set(CATEGORY_KEY_MAP)
        )
        if unmapped_labels:
            print(f"\nNote: no mapping for these row(s), skipping them entirely: {unmapped_labels}")

        months_saved = 0
        months_skipped = 0

        for month_index, month_col in enumerate(MONTH_COLUMNS, start=1):
            if month_col not in df.columns:
                continue
            report_date = date_type(args.year, month_index, 1)

            expense_rows: list[dict] = []
            for _, row in df.iterrows():
                label = str(row["CATEGORY"]).strip()
                key = CATEGORY_KEY_MAP.get(label)
                if key is None:
                    continue
                amount = money(row[month_col])
                if amount == 0:
                    continue
                category = category_by_key.get(key)
                if category is None:
                    print(f"WARNING: category key '{key}' (from '{label}') not found for this org — skipping that line.")
                    continue
                expense_rows.append({"description": label, "amount": amount, "expense_category_id": category.id})

            if not expense_rows:
                continue

            existing_reports = db.execute(
                select(DailyReport)
                .where(DailyReport.organization_id == organization.id, DailyReport.report_date == report_date)
                .options(selectinload(DailyReport.expenses))
            ).scalars().all()
            existing_descriptions = {e.description for r in existing_reports for e in r.expenses}
            batch_descriptions = {r["description"] for r in expense_rows}
            if existing_descriptions & batch_descriptions:
                print(f"\n{report_date} ({month_col.title()}): expenses already imported — skipping.")
                months_skipped += 1
                continue

            total = sum((r["amount"] for r in expense_rows), Decimal("0"))
            print(f"\n---- {month_col.title()} {args.year} ({report_date}) ----")
            for r in expense_rows:
                print(f"  {r['description']:<35} £{r['amount']}")
            print(f"  {'TOTAL':<35} £{total}")

            if args.dry_run:
                print("  (dry run — not saved)")
                continue

            payload = DailyReportSavePayload(
                values={},
                expenses=[
                    ExpenseIn(description=r["description"], amount=r["amount"], expense_category_id=r["expense_category_id"])
                    for r in expense_rows
                ],
                prepared_by=None,
                checked_by=None,
            )
            saved = save_daily_report(db=db, organization_id=organization.id, report_date=report_date, payload=payload, actor_id=actor_id)
            print(f"  Saved report {saved.id} — {len(expense_rows)} expense lines")
            months_saved += 1

        print("\n==================================")
        print("IMPORT COMPLETE" if not args.dry_run else "DRY RUN COMPLETE")
        print("==================================")
        print(f"Months saved: {months_saved}  Months skipped (already present): {months_skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
