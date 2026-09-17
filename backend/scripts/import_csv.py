"""Import a daily sales tracker (CSV or Excel) into MAARA via the normal
save_daily_report() path — the same validation, calculation engine, and
persistence a manual form Save would go through.

Column names are matched loosely (case/whitespace-insensitive, first match
wins) so this works against both the original "daily sales tracker (1).xlsx"
export and the newer dosa-chutney-sales-*.csv shape without edits.

Usage:
    python scripts/import_csv.py --file "C:\\Users\\Admin\\Downloads\\dosa-chutney-sales-june.csv"
    python scripts/import_csv.py --file tracker.xlsx --sheet "Daily Sales & Expense Report"
    python scripts/import_csv.py --file june.csv --dry-run
    python scripts/import_csv.py --file june.csv --limit 5
"""
from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database.connection import SessionLocal  # noqa: E402
from database.models import Organization, OrganizationMember  # noqa: E402
from repositories import daily_report_repository, template_repository  # noqa: E402
from schemas.daily_report import DailyReportSavePayload  # noqa: E402
from services.report_service import TEMPLATE_KEY, save_daily_report  # noqa: E402

# Each logical field accepts several possible source header spellings —
# whichever is present in the file wins. Keeps one script working for both
# the CSV and the older Excel export without a format flag.
COLUMN_CANDIDATES: dict[str, list[str]] = {
    "date": ["Date"],
    "card_till": ["Card Sales (Till)", "Daily Card sales(Till)"],
    "card_machine": ["Card Sales (Machine)", "Daily Card sales(Mach)"],
    "cash": ["Cash Sales"],
    "uber": ["Uber Eats", "Uber eats Sales"],
    "just_eat": ["Just Eats", "Just Eats sales"],
    "deliveroo": ["Deliveroo", "Deliveroo Sales"],
    "website": ["Website", "Fusion Pos Sales (Website)"],
    "others": ["Others"],
    "tips": ["Tips on Card", "Tips on Card "],
    "payout": ["Payout"],
    "cash_balance": ["Cash balance After PAYOUT", "Cash Balance After Payout", "Cash balance After Payout"],
    "total_sales": ["Total Sales"],
}


def _norm(name: str) -> str:
    return " ".join(str(name).split()).strip().lower()


def resolve_columns(columns: list[str]) -> dict[str, str]:
    """Maps each logical field to whichever actual column header is present."""
    by_norm = {_norm(c): c for c in columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for field, candidates in COLUMN_CANDIDATES.items():
        match = next((by_norm[_norm(c)] for c in candidates if _norm(c) in by_norm), None)
        if match is None:
            # card_machine/tips/payout may genuinely be absent from an older
            # export — everything else is required to compute/validate totals.
            if field in ("card_machine", "tips", "payout"):
                continue
            missing.append(field)
        else:
            resolved[field] = match
    if missing:
        raise RuntimeError(f"Couldn't find a column for: {', '.join(missing)}. Available columns: {list(columns)}")
    return resolved


def money(value) -> Decimal:
    if pd.isna(value):
        return Decimal("0")
    text = str(value).strip().replace("£", "").replace(",", "").replace(" ", "")
    if text == "":
        return Decimal("0")
    try:
        return Decimal(text)
    except InvalidOperation:
        print(f"WARNING: Could not convert '{value}' to money.")
        return Decimal("0")


def value_string(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01")))


def load_rows(file_path: Path, sheet: str | None) -> pd.DataFrame:
    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path, sheet_name=sheet or "Daily Sales & Expense Report")

    columns = resolve_columns(list(df.columns))
    df = df.rename(columns={source: field for field, source in columns.items()})
    df = df.dropna(subset=["date"])
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", required=True, type=Path, help="Path to a .csv or .xlsx sales tracker export.")
    parser.add_argument("--org-slug", default="dosa-n-chutney", help="Organization slug to import into.")
    parser.add_argument("--sheet", default=None, help="Excel sheet name (Excel files only).")
    parser.add_argument("--limit", type=int, default=None, help="Only import the first N rows.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without saving anything.")
    args = parser.parse_args()

    print("\n==================================")
    print("MAARA SALES IMPORT")
    print("==================================")
    print(f"\nReading: {args.file}")

    if not args.file.exists():
        raise FileNotFoundError(f"File does not exist:\n{args.file}")

    df = load_rows(args.file, args.sheet)
    if args.limit is not None:
        df = df.head(args.limit)
    print(f"\nRows to import: {len(df)}")

    db = SessionLocal()
    try:
        organization = db.execute(select(Organization).where(Organization.slug == args.org_slug)).scalar_one_or_none()
        if organization is None:
            raise RuntimeError(f"Organization '{args.org_slug}' was not found.")
        print(f"\nOrganization: {organization.name} ({organization.id})")

        member = db.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization.id)
            .order_by(OrganizationMember.created_at)
        ).scalars().first()
        if member is None:
            raise RuntimeError("No organization member exists. Create/login with your MAARA user first.")
        actor_id = member.user_id
        print(f"Import actor: {actor_id}")

        templates = template_repository.list_templates(db, organization.id)
        template = next((t for t in templates if t.key == TEMPLATE_KEY), None)
        if template is None or template.current_version_id is None:
            raise RuntimeError(f"Organization '{args.org_slug}' has no published '{TEMPLATE_KEY}' template yet.")
        version = template_repository.get_version(db, organization.id, template.id, template.current_version_id)
        has_split_card = any(f.key == "card_sales_machine" for section in version.sections for f in section.fields)

        imported = 0
        skipped = 0
        mismatches = 0

        for _, row in df.iterrows():
            report_date = row["date"].date()

            existing = daily_report_repository.get_by_date(db, organization.id, template.id, report_date)
            if existing is not None:
                print(f"\n{report_date}: already imported (report {existing.id}) — skipping.")
                skipped += 1
                continue

            card_till = money(row["card_till"])
            card_machine = money(row.get("card_machine", 0)) if "card_machine" in row else Decimal("0")
            cash = money(row["cash"])
            uber = money(row["uber"])
            just_eat = money(row["just_eat"])
            deliveroo = money(row["deliveroo"])
            website = money(row["website"])
            others = money(row["others"])
            tips = money(row["tips"]) if "tips" in row else Decimal("0")
            payout = money(row["payout"]) if "payout" in row else Decimal("0")
            cash_balance = money(row["cash_balance"])
            excel_total = money(row["total_sales"])

            other_sales = website + others
            # Total Sales is built from the card machine reading, not the till —
            # verified against the source file: Machine + Cash + delivery
            # platforms + Website/Others matches Total Sales on every row.
            revenue_card = card_machine if has_split_card else card_till
            calculated_total = revenue_card + cash + uber + just_eat + deliveroo + other_sales
            difference = abs(calculated_total - excel_total)

            print(f"\n----------------------------------\nDate: {report_date}\n----------------------------------")
            print(f"Card Till:      £{card_till}")
            print(f"Card Machine:   £{card_machine}")
            print(f"Cash:           £{cash}")
            print(f"Uber Eats:      £{uber}")
            print(f"Just Eat:       £{just_eat}")
            print(f"Deliveroo:      £{deliveroo}")
            print(f"Other Sales:    £{other_sales}  (website {website} + others {others})")
            print(f"Tips:           £{tips}")
            print(f"Payout:         £{payout}")
            print(f"Calculated:     £{calculated_total}")
            print(f"Source Total:   £{excel_total}")
            print(f"Difference:     £{difference}")

            if difference > Decimal("0.05"):
                # The source tracker itself has occasional data-entry slips (e.g.
                # a Till figure typed into a Total Sales cell, or a cell left
                # stale) — warn loudly instead of aborting the whole import.
                # The calculated total (from the components) is always what
                # gets saved: the backend's calculation engine never trusts a
                # submitted total_sales value either way.
                print(f"WARNING: source Total Sales (£{excel_total}) doesn't match the calculated total "
                      f"(£{calculated_total}) — saving the calculated total anyway; check this row in the source file.")
                mismatches += 1
            else:
                print("Total matches source")

            if args.dry_run:
                print("(dry run — not saved)")
                continue

            values = {
                "opening_cash": "0",
                "cash_sales": value_string(cash),
                "uber_eats": value_string(uber),
                "just_eat": value_string(just_eat),
                "deliveroo": value_string(deliveroo),
                "other_sales": value_string(other_sales),
                "misc_income": "0",
                "next_day_open_cash": "0",
                "cash_balance": value_string(cash_balance),
            }
            if has_split_card:
                values["card_sales_till"] = value_string(card_till)
                values["card_sales_machine"] = value_string(card_machine)
                values["tips_on_card"] = value_string(tips)
                values["payout"] = value_string(payout)
            else:
                values["card_sales"] = value_string(card_till)

            payload = DailyReportSavePayload(values=values, expenses=[], prepared_by=None, checked_by=None)
            saved = save_daily_report(db=db, organization_id=organization.id, report_date=report_date, payload=payload, actor_id=actor_id)
            print(f"Saved report {saved.id} — Total Sales £{saved.values.get('total_sales')}")
            imported += 1

        print("\n==================================")
        print("IMPORT COMPLETE" if not args.dry_run else "DRY RUN COMPLETE")
        print("==================================")
        print(f"Imported: {imported}  Skipped (already present): {skipped}  Source/calculated mismatches: {mismatches}  Total rows: {len(df)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
