from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

ROLES = ("owner", "admin", "manager", "staff")


class OrganizationMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Joins a profile to an organization with a role. The unit authorization checks against."""

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member_org_user"),
        CheckConstraint("role IN ('owner','admin','manager','staff')", name="ck_org_member_role"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="members")
    profile: Mapped[Profile] = relationship(back_populates="memberships")

    def __repr__(self) -> str:
        return f"<OrganizationMember org={self.organization_id} user={self.user_id} role={self.role}>"
