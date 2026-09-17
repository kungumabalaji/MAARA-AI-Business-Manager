import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.dependencies import get_db
from auth.permissions import require_role
from database.models import OrganizationMember
from services import dashboard_service

router = APIRouter(prefix="/organizations/{organization_id}/dashboard", tags=["dashboards"])


# le=100000 (~270 years) is the "All-time" sentinel — the frontend range filter
# sends a very large window to mean "everything".
_MAX_DAYS = 100_000


@router.get("/sales/daily")
def sales_daily(
    organization_id: uuid.UUID,
    days: int = Query(default=21, ge=1, le=_MAX_DAYS),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.sales_daily(db, organization_id, days)


@router.get("/expenses/daily")
def expenses_daily(
    organization_id: uuid.UUID,
    days: int = Query(default=90, ge=1, le=_MAX_DAYS),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.expenses_daily(db, organization_id, days)


@router.get("/sales/monthly")
def sales_monthly(
    organization_id: uuid.UUID,
    months: int = Query(default=7, ge=1, le=24),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.sales_monthly(db, organization_id, months)


@router.get("/sales/monthly-summary")
def sales_month_summary(
    organization_id: uuid.UUID,
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.sales_month_summary(db, organization_id, year, month)


@router.get("/expenses/monthly")
def expenses_monthly(
    organization_id: uuid.UUID,
    months: int = Query(default=7, ge=1, le=24),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.expenses_monthly(db, organization_id, months)


@router.get("/expenses/categories")
def expenses_categories(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.list_expense_categories(db, organization_id)


@router.get("/expenses/by-category")
def expenses_by_category(
    organization_id: uuid.UUID,
    since: date_type = Query(...),
    until: date_type = Query(...),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.expenses_by_category(db, organization_id, since, until)


@router.get("/expenses/recent")
def expenses_recent(
    organization_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=500),
    since: date_type | None = Query(default=None),
    until: date_type | None = Query(default=None),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.expenses_recent(db, organization_id, limit, since, until)


@router.get("/profit/monthly")
def profit_monthly(
    organization_id: uuid.UUID,
    months: int = Query(default=7, ge=1, le=24),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.profit_monthly(db, organization_id, months)


@router.get("/profit/daily-summary")
def profit_daily_summary(
    organization_id: uuid.UUID,
    report_date: date_type | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.daily_summary(db, organization_id, report_date)
