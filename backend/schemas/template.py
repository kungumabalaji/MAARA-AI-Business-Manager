import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FieldIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    field_type: str = Field(pattern=r"^(money|number|percentage|text|date)$")
    required: bool = False
    is_calculated: bool = False
    display_order: int = 0
    field_metadata: dict | None = None


class FieldOut(FieldIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class SectionIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    display_order: int = 0
    fields: list[FieldIn] = Field(default_factory=list)


class SectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    key: str
    label: str
    display_order: int
    fields: list[FieldOut]


class CalculationRuleIn(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    operation: str
    operands: dict


class CalculationRuleOut(CalculationRuleIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class TemplateVersionCreate(BaseModel):
    """Payload for drafting a new version — either from scratch or as an edit."""

    sections: list[SectionIn]
    calculation_rules: list[CalculationRuleIn]


class TemplateVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    report_template_id: uuid.UUID
    version_number: int
    status: str
    published_at: datetime | None
    sections: list[SectionOut]
    calculation_rules: list[CalculationRuleOut]


class ReportTemplateCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    name: str


class ReportTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    key: str
    name: str
    current_version_id: uuid.UUID | None
