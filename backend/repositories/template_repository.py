"""DB access for the template engine. Every function here takes organization_id

explicitly and filters by it — this is the layer where "never trust the client's
organization_id" turns into an actual WHERE clause.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import ReportField, ReportSection, ReportTemplate, ReportTemplateVersion


def get_template(db: Session, organization_id: uuid.UUID, template_id: uuid.UUID) -> ReportTemplate | None:
    return db.execute(
        select(ReportTemplate).where(
            ReportTemplate.id == template_id,
            ReportTemplate.organization_id == organization_id,
        )
    ).scalar_one_or_none()


def list_templates(db: Session, organization_id: uuid.UUID) -> list[ReportTemplate]:
    return list(
        db.execute(select(ReportTemplate).where(ReportTemplate.organization_id == organization_id)).scalars()
    )


def get_version(
    db: Session, organization_id: uuid.UUID, template_id: uuid.UUID, version_id: uuid.UUID
) -> ReportTemplateVersion | None:
    return db.execute(
        select(ReportTemplateVersion)
        .join(ReportTemplate, ReportTemplate.id == ReportTemplateVersion.report_template_id)
        .where(
            ReportTemplateVersion.id == version_id,
            ReportTemplateVersion.report_template_id == template_id,
            ReportTemplate.organization_id == organization_id,
        )
        .options(
            selectinload(ReportTemplateVersion.sections).selectinload(ReportSection.fields),
            selectinload(ReportTemplateVersion.calculation_rules),
        )
    ).scalar_one_or_none()


def get_current_version(
    db: Session, organization_id: uuid.UUID, template_id: uuid.UUID
) -> ReportTemplateVersion | None:
    template = get_template(db, organization_id, template_id)
    if template is None or template.current_version_id is None:
        return None
    return get_version(db, organization_id, template_id, template.current_version_id)


def next_version_number(db: Session, template_id: uuid.UUID) -> int:
    existing = db.execute(
        select(ReportTemplateVersion.version_number).where(ReportTemplateVersion.report_template_id == template_id)
    ).scalars()
    numbers = list(existing)
    return (max(numbers) + 1) if numbers else 1


def load_fields_flat(version: ReportTemplateVersion) -> list[ReportField]:
    return [f for section in version.sections for f in section.fields]
