"""Template versioning business logic. The one rule that matters most: a

version's sections/fields/rules can only be written while status == "draft",
and publish() is the only path that ever flips a version to "published" — and
it refuses to do that unless calculations.evaluator proves the rule set sound.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from calculations.errors import CalculationError
from calculations.evaluator import FieldSpec, RuleSpec, validate_rules
from database.models import (
    CalculationRule,
    ReportField,
    ReportSection,
    ReportTemplate,
    ReportTemplateVersion,
)
from repositories import template_repository
from schemas.template import TemplateVersionCreate


def create_draft_version(
    db: Session,
    organization_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: TemplateVersionCreate,
    created_by: uuid.UUID,
) -> ReportTemplateVersion:
    template = template_repository.get_template(db, organization_id, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report template not found.")

    version = ReportTemplateVersion(
        report_template_id=template.id,
        version_number=template_repository.next_version_number(db, template.id),
        status="draft",
        created_by=created_by,
    )
    db.add(version)
    db.flush()  # assigns version.id without committing, so children can FK to it

    for section_in in payload.sections:
        section = ReportSection(
            template_version_id=version.id,
            key=section_in.key,
            label=section_in.label,
            display_order=section_in.display_order,
        )
        db.add(section)
        db.flush()

        for field_in in section_in.fields:
            db.add(
                ReportField(
                    section_id=section.id,
                    key=field_in.key,
                    label=field_in.label,
                    field_type=field_in.field_type,
                    required=field_in.required,
                    is_calculated=field_in.is_calculated,
                    display_order=field_in.display_order,
                    field_metadata=field_in.field_metadata,
                )
            )

    for rule_in in payload.calculation_rules:
        db.add(
            CalculationRule(
                template_version_id=version.id,
                key=rule_in.key,
                operation=rule_in.operation,
                operands=rule_in.operands,
            )
        )

    db.commit()
    db.refresh(version)
    return template_repository.get_version(db, organization_id, template_id, version.id)  # reload with relationships


def _to_engine_inputs(version: ReportTemplateVersion) -> tuple[list[FieldSpec], list[RuleSpec]]:
    fields = [
        FieldSpec(key=f.key, section_key=section.key, is_calculated=f.is_calculated)
        for section in version.sections
        for f in section.fields
    ]
    rules = [RuleSpec(key=r.key, operation=r.operation, operands=r.operands) for r in version.calculation_rules]
    return fields, rules


def publish_version(
    db: Session, organization_id: uuid.UUID, template_id: uuid.UUID, version_id: uuid.UUID
) -> ReportTemplateVersion:
    version = template_repository.get_version(db, organization_id, template_id, version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template version not found.")
    if version.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only a draft version can be published (this one is '{version.status}').",
        )

    fields, rules = _to_engine_inputs(version)
    try:
        validate_rules(fields, rules)
    except CalculationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    version.status = "published"
    version.published_at = datetime.now(UTC)

    template = db.get(ReportTemplate, template_id)
    template.current_version_id = version.id

    db.commit()
    db.refresh(version)
    return version
