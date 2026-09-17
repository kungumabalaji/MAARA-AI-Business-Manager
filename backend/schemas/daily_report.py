import uuid
from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ExpenseIn(BaseModel):
    description: str
    amount: Decimal
    expense_category_id: uuid.UUID | None = None
    notes: str | None = None


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    description: str
    amount: Decimal
    expense_category_id: uuid.UUID | None
    notes: str | None


class DailyReportSavePayload(BaseModel):
    """What the daily-entry form actually sends: raw field values keyed by

    report_fields.key, the expense rows, and the two sign-off selections.
    Calculated fields (total_sales, total_expenses, operating_profit, ...) are
    never accepted here even if present — the server always recomputes them.
    """

    values: dict[str, str]
    expenses: list[ExpenseIn]
    prepared_by: uuid.UUID | None = None
    checked_by: uuid.UUID | None = None


class DailyReportOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    report_date: date_type
    status: str
    values: dict[str, str]
    expenses: list[ExpenseOut]
    prepared_by: uuid.UUID | None
    checked_by: uuid.UUID | None


class DailyReportListOut(BaseModel):
    items: list[DailyReportOut]
    total: int
