from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base, TimestampMixin


class Profile(Base, TimestampMixin):
    """Mirrors auth.users — id matches the Supabase auth user id exactly.

    Populated by a Postgres trigger on auth.users AFTER INSERT (see the initial
    migration). Never created ad hoc from application code, and never carries a
    server-generated id of its own — it must equal auth.users.id.
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    memberships: Mapped[list[OrganizationMember]] = relationship(back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile {self.id}>"
