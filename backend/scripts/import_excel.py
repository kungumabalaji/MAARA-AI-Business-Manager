from services.report_service import save_daily_report
from schemas.daily_report import DailyReportSavePayload
from database.models import Organization, OrganizationMember
from database.connection import SessionLocal
from pathlib import Path
import sys
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import select


# =========================================================
# 1. Make BACKEND imports available
# =========================================================

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# IMPORTANT:
# These imports must come AFTER sys.path is configured.


# =========================================================
# 2. SETTINGS
# =========================================================

EXCEL_FILE = Path(
    r"C:\Users\Admin\Downloads\daily sales tracker (1).xlsx"
)

SHEET_NAME = "Daily Sales & Expense Report"

ORGANIZATION_SLUG = "dosa-n-chutney"

# First test only 5 rows.
IMPORT_LIMIT = 5


# =========================================================
# 3. Convert Excel values safely to money
# =========================================================

def money(value) -> Decimal:
    if pd.isna(value):
        return Decimal("0")

    text = str(value).strip()

    text = (
        text.replace("£", "")
        .replace(",", "")
        .replace(" ", "")
    )

    if text == "":
        return Decimal("0")

    try:
        return Decimal(text)

    except InvalidOperation:
        print(f"WARNING: Could not convert '{value}' to money.")
        return Decimal("0")


def value_string(value: Decimal) -> str:
    return str(
        value.quantize(Decimal("0.01"))
    )


# =========================================================
# 4. Check Excel file
# =========================================================

print("\n==================================")
print("MAARA EXCEL IMPORT")
print("==================================")

print("\nReading Excel:")
print(EXCEL_FILE)

if not EXCEL_FILE.exists():
    raise FileNotFoundError(
        f"Excel file does not exist:\n{EXCEL_FILE}"
    )


# =========================================================
# 5. Read Excel sheet
# =========================================================

df = pd.read_excel(
    EXCEL_FILE,
    sheet_name=SHEET_NAME,
)


# =========================================================
# 6. Clean Excel dates
# =========================================================

df = df.dropna(
    subset=["Date"]
)

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce",
)

df = df.dropna(
    subset=["Date"]
)


# =========================================================
# 7. TEST ONLY FIRST 5 ROWS
# =========================================================

df = df.head(IMPORT_LIMIT)

print(f"\nRows to import: {len(df)}")


# =========================================================
# 8. Connect to Supabase PostgreSQL
# =========================================================

db = SessionLocal()


try:

    # =====================================================
    # Find organization
    # =====================================================

    organization = db.execute(
        select(Organization).where(
            Organization.slug == ORGANIZATION_SLUG
        )
    ).scalar_one_or_none()

    if organization is None:
        raise RuntimeError(
            f"Organization '{ORGANIZATION_SLUG}' "
            "was not found in Supabase."
        )

    print("\nOrganization:")
    print(organization.name)
    print(organization.id)

    # =====================================================
    # Find a MAARA organization member
    # =====================================================

    member = db.execute(
        select(OrganizationMember)
        .where(
            OrganizationMember.organization_id
            == organization.id
        )
        .order_by(
            OrganizationMember.created_at
        )
    ).scalars().first()

    if member is None:
        raise RuntimeError(
            "No organization member exists. "
            "Create/login with your MAARA user first."
        )

    actor_id = member.user_id

    print("\nImport actor:")
    print(actor_id)

    # =====================================================
    # 9. Import each Excel row
    # =====================================================

    for index, row in df.iterrows():

        report_date = row["Date"].date()

        # -------------------------------------------------
        # SALES
        # -------------------------------------------------

        card_sales = money(
            row["Daily Card sales(Till)"]
        )

        cash_sales = money(
            row["Cash Sales"]
        )

        uber_sales = money(
            row["Uber eats Sales"]
        )

        just_eat_sales = money(
            row["Just Eats sales"]
        )

        deliveroo_sales = money(
            row["Deliveroo Sales"]
        )

        fusion_sales = money(
            row["Fusion Pos Sales (Website)"]
        )

        others_excel = money(
            row["Others"]
        )

        tips_on_card = money(
            row["Tips on Card "]
        )

        # -------------------------------------------------
        # Current MAARA only has one "Other Sales" field.
        #
        # For now:
        #
        # Fusion POS
        # + Others
        # + Tips
        # =
        # MAARA Other Sales
        # -------------------------------------------------

        other_sales = (
            fusion_sales
            + others_excel
            + tips_on_card
        )

        # -------------------------------------------------
        # CASH BALANCE
        # -------------------------------------------------

        cash_balance = money(
            row["Cash balance After PAYOUT"]
        )

        # -------------------------------------------------
        # Excel total for validation only
        # -------------------------------------------------

        excel_total = money(
            row["Total Sales"]
        )

        # -------------------------------------------------
        # Calculate what MAARA should calculate
        # -------------------------------------------------

        calculated_total = (
            card_sales
            + cash_sales
            + uber_sales
            + just_eat_sales
            + deliveroo_sales
            + other_sales
        )

        difference = abs(
            calculated_total - excel_total
        )

        print("\n----------------------------------")
        print(f"Date: {report_date}")
        print("----------------------------------")

        print(f"Card Till:       £{card_sales}")
        print(f"Cash Sales:      £{cash_sales}")
        print(f"Uber Eats:       £{uber_sales}")
        print(f"Just Eat:        £{just_eat_sales}")
        print(f"Deliveroo:       £{deliveroo_sales}")
        print(f"Fusion Website:  £{fusion_sales}")
        print(f"Others:          £{others_excel}")
        print(f"Tips:            £{tips_on_card}")

        print()
        print(f"Calculated:      £{calculated_total}")
        print(f"Excel Total:     £{excel_total}")
        print(f"Difference:      £{difference}")

        # -------------------------------------------------
        # Stop if our mapping is wrong.
        # -------------------------------------------------

        if difference > Decimal("0.05"):

            print("\nERROR: TOTAL DOES NOT MATCH.")
            print("Nothing for this row will be imported.")

            raise RuntimeError(
                f"Sales mapping failed for {report_date}. "
                f"Difference: £{difference}"
            )

        print("✓ Total matches Excel")

        # =================================================
        # 10. Map Excel → MAARA fields
        # =================================================

        values = {

            "opening_cash": "0",

            "card_sales":
                value_string(card_sales),

            "cash_sales":
                value_string(cash_sales),

            "uber_eats":
                value_string(uber_sales),

            "just_eat":
                value_string(just_eat_sales),

            "deliveroo":
                value_string(deliveroo_sales),

            "other_sales":
                value_string(other_sales),

            "misc_income": "0",

            "next_day_open_cash": "0",

            "cash_balance":
                value_string(cash_balance),
        }

        # =================================================
        # 11. Create MAARA payload
        # =================================================

        payload = DailyReportSavePayload(

            values=values,

            # Payout is NOT imported as an expense yet.
            expenses=[],

            prepared_by=None,

            checked_by=None,
        )

        # =================================================
        # 12. Save through existing MAARA service
        # =================================================

        print(
            f"\nSaving {report_date} "
            "to Supabase..."
        )

        saved = save_daily_report(

            db=db,

            organization_id=organization.id,

            report_date=report_date,

            payload=payload,

            actor_id=actor_id,
        )

        print(
            f"✓ Saved report ID: {saved.id}"
        )

        if "total_sales" in saved.values:

            print(
                "MAARA Total Sales:",
                f"£{saved.values['total_sales']}"
            )

    # =====================================================
    # COMPLETE
    # =====================================================

    print("\n==================================")
    print("IMPORT COMPLETE")
    print("==================================")

    print(
        f"Successfully processed "
        f"{len(df)} Excel rows."
    )


finally:

    db.close()
