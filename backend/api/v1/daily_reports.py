import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, get_db
from auth.permissions import require_role
from auth.schemas import AuthenticatedUser
from database.models import OrganizationMember
from schemas.daily_report import DailyReportListOut, DailyReportOut, DailyReportSavePayload
from services import report_service

router = APIRouter(prefix="/organizations/{organization_id}/daily-reports", tags=["daily-reports"])


@router.get("/by-date/{report_date}", response_model=DailyReportOut | None)
def read_daily_report(
    organization_id: uuid.UUID,
    report_date: date_type,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return report_service.get_daily_report(db, organization_id, report_date)


@router.put("/by-date/{report_date}", response_model=DailyReportOut)
def save_daily_report(
    organization_id: uuid.UUID,
    report_date: date_type,
    payload: DailyReportSavePayload,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return report_service.save_daily_report(db, organization_id, report_date, payload, actor_id=user.id)


@router.get("", response_model=DailyReportListOut)
def list_daily_reports(
    organization_id: uuid.UUID,
    since: date_type | None = Query(default=None),
    until: date_type | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return report_service.list_daily_reports(db, organization_id, since, until, page, page_size)


@router.get("/{report_id}", response_model=DailyReportOut)
def read_daily_report_by_id(
    organization_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    report = report_service.get_daily_report_by_id(db, organization_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report


@router.put("/{report_id}", response_model=DailyReportOut)
def update_daily_report(
    organization_id: uuid.UUID,
    report_id: uuid.UUID,
    payload: DailyReportSavePayload,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    return report_service.update_daily_report(db, organization_id, report_id, payload, actor_id=user.id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_report(
    organization_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("manager")),
):
    report_service.delete_daily_report(db, organization_id, report_id)
