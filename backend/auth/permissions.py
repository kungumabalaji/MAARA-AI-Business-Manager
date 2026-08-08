"""Org-membership and role gating. Every route in api/v1/ that touches a

specific organization's data depends on get_membership (or require_role, which
wraps it) — organization_id always comes from the URL path and is checked
against a real membership row here. It is never taken on trust from the client.
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user, get_db
from auth.schemas import AuthenticatedUser
from database.models import OrganizationMember

ROLE_RANK = {"staff": 0, "manager": 1, "admin": 2, "owner": 3}


def get_membership(
    organization_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> OrganizationMember:
    membership = db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
    ).scalar_one_or_none()

    if membership is None:
        # Deliberately the same error whether the org doesn't exist or the
        # caller just isn't a member of it — don't leak which.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this organization.",
        )

    return membership


def require_role(minimum_role: str) -> Callable[..., OrganizationMember]:
    """require_role("manager") gates a route to manager, admin, or owner."""

    if minimum_role not in ROLE_RANK:
        raise ValueError(f"Unknown role: {minimum_role!r}. Expected one of {list(ROLE_RANK)}.")

    def dependency(membership: OrganizationMember = Depends(get_membership)) -> OrganizationMember:
        if ROLE_RANK[membership.role] < ROLE_RANK[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires the '{minimum_role}' role or higher.",
            )
        return membership

    return dependency
