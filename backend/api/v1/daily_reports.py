import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, get_db
from auth.permissions import require_role
from auth.schemas import AuthenticatedUser
from database.models import OrganizationMember
from schemas.daily_report import DailyReportOut, DailyReportSavePayload
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
