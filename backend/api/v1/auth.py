from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user, get_db
from auth.schemas import AuthenticatedUser, MeResponse, OrganizationMembershipOut, ProfileOut
from database.models import Organization, OrganizationMember, Profile

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=MeResponse)
def read_me(
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Verifies the bearer token and returns who the caller is and which

    organizations they belong to, with what role in each. The frontend calls
    this once after Supabase sign-in to bootstrap the session.
    """
    profile = db.get(Profile, user.id)
    if profile is None:
        # The auth.users → profiles trigger fires on signup; a brand-new token
        # from a user created outside that path (or a race on first request)
        # can arrive before the row exists. Self-heal rather than 500.
        profile = Profile(id=user.id, display_name=user.email)
        db.add(profile)
        db.commit()
        db.refresh(profile)

    rows = db.execute(
        select(OrganizationMember, Organization)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == user.id)
    ).all()

    return MeResponse(
        profile=ProfileOut.model_validate(profile),
        organizations=[
            OrganizationMembershipOut(
                organization_id=org.id,
                organization_name=org.name,
                organization_slug=org.slug,
                role=member.role,
            )
            for member, org in rows
        ],
    )
