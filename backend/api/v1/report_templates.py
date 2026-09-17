import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, get_db
from auth.permissions import require_role
from auth.schemas import AuthenticatedUser
from database.models import OrganizationMember, ReportTemplate
from repositories import template_repository
from schemas.template import (
    ReportTemplateCreate,
    ReportTemplateOut,
    TemplateVersionCreate,
    TemplateVersionOut,
)
from services import template_service

router = APIRouter(prefix="/organizations/{organization_id}/report-templates", tags=["report-templates"])


@router.get("", response_model=list[ReportTemplateOut])
def list_templates(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
) -> list[ReportTemplate]:
    return template_repository.list_templates(db, organization_id)


@router.post("", response_model=ReportTemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(
    organization_id: uuid.UUID,
    payload: ReportTemplateCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
    membership: OrganizationMember = Depends(require_role("admin")),
) -> ReportTemplate:
    template = ReportTemplate(
        organization_id=organization_id,
        key=payload.key,
        name=payload.name,
        created_by=user.id,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}/versions/{version_id}", response_model=TemplateVersionOut)
def read_version(
    organization_id: uuid.UUID,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    version = template_repository.get_version(db, organization_id, template_id, version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template version not found.")
    return version


@router.get("/{template_id}/current-version", response_model=TemplateVersionOut)
def read_current_version(
    organization_id: uuid.UUID,
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("staff")),
):
    version = template_repository.get_current_version(db, organization_id, template_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This template has no published version yet.")
    return version


@router.post("/{template_id}/versions", response_model=TemplateVersionOut, status_code=status.HTTP_201_CREATED)
def create_version(
    organization_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: TemplateVersionCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
    membership: OrganizationMember = Depends(require_role("admin")),
):
    return template_service.create_draft_version(db, organization_id, template_id, payload, created_by=user.id)


@router.post("/{template_id}/versions/{version_id}/publish", response_model=TemplateVersionOut)
def publish_version(
    organization_id: uuid.UUID,
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    membership: OrganizationMember = Depends(require_role("admin")),
):
    return template_service.publish_version(db, organization_id, template_id, version_id)
