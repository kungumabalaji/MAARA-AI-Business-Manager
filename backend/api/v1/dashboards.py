import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.dependencies import get_db
from auth.permissions import require_role
from database.models import OrganizationMember
from services import dashboard_service

router = APIRouter(prefix="/organizations/{organization_id}/dashboard", tags=["dashboards"])


@router.get("/sales/daily")
def sales_daily(
    organization_id: uuid.UUID,
    days: int = Query(default=21, ge=1, le=180),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.sales_daily(db, organization_id, days)


@router.get("/sales/monthly")
def sales_monthly(
    organization_id: uuid.UUID,
    months: int = Query(default=7, ge=1, le=24),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.sales_monthly(db, organization_id, months)


@router.get("/expenses/monthly")
def expenses_monthly(
    organization_id: uuid.UUID,
    months: int = Query(default=7, ge=1, le=24),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.expenses_monthly(db, organization_id, months)


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
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return dashboard_service.expenses_recent(db, organization_id, limit)


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
