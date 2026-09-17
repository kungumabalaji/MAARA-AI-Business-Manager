"""profiles fk to auth users

Revision ID: 6a5356d68eec
Revises: 58a177b1c0cd
Create Date: 2026-08-08 14:46:05.264015

The initial migration created profiles.id as a plain UUID PK without a foreign
key back to auth.users — the trigger populated it correctly, but nothing
enforced referential integrity or cleaned it up when an auth user was deleted.
This adds that constraint, discovered by actually deleting a real test user
end-to-end and finding the orphaned profile left behind.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6a5356d68eec'
down_revision: str | Sequence[str] | None = '58a177b1c0cd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE public.profiles
        ADD CONSTRAINT fk_profiles_auth_user
        FOREIGN KEY (id) REFERENCES auth.users (id) ON DELETE CASCADE;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE public.profiles DROP CONSTRAINT fk_profiles_auth_user;")
