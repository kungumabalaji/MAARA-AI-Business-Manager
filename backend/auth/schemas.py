import uuid

from pydantic import BaseModel, ConfigDict


class AuthenticatedUser(BaseModel):
    """The verified identity of the caller — derived from the JWT, nothing else.

    Never constructed from anything the client sends outside the token itself.
    """

    id: uuid.UUID
    email: str | None = None


class OrganizationMembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role: str


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str | None = None


class MeResponse(BaseModel):
    profile: ProfileOut
    organizations: list[OrganizationMembershipOut]
