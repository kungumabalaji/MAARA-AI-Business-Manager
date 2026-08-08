"""One-off admin script: make a real, already-signed-up user the owner of an

organization. Needed because the Dosa n Chutney org and template are seeded by
migration (before any real person exists to attach as a member) — run this
once, after that person has signed in for real at least once, so their
profiles row exists.

Usage:
    .venv/Scripts/python scripts/grant_org_owner.py <email> [--org-slug dosa-n-chutney]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make backend/ importable regardless of cwd

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Organization, OrganizationMember, Profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("email", help="Email of the already-signed-up user, matched via Supabase auth metadata isn't stored here — pass the profile id instead if you have it, or see --profile-id.")
    parser.add_argument("--profile-id", help="Profile UUID (== Supabase auth user id) if you have it directly.")
    parser.add_argument("--org-slug", default="dosa-n-chutney")
    parser.add_argument("--role", default="owner", choices=["owner", "admin", "manager", "staff"])
    args = parser.parse_args()

    db = SessionLocal()
    try:
        organization = db.execute(select(Organization).where(Organization.slug == args.org_slug)).scalar_one_or_none()
        if organization is None:
            sys.exit(f"No organization with slug '{args.org_slug}'.")

        if args.profile_id:
            profile = db.get(Profile, args.profile_id)
        else:
            # display_name is seeded from the Supabase signup email by /me on first
            # call — this is a convenience match, not an authoritative email lookup.
            profile = db.execute(select(Profile).where(Profile.display_name == args.email)).scalar_one_or_none()

        if profile is None:
            sys.exit(
                f"No profile found for '{args.email}'. They need to sign in at least once "
                "first (which creates their profiles row), then re-run this with --profile-id."
            )

        existing = db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id,
                OrganizationMember.user_id == profile.id,
            )
        ).scalar_one_or_none()

        if existing:
            existing.role = args.role
            print(f"Updated existing membership -> role={args.role}")
        else:
            db.add(OrganizationMember(organization_id=organization.id, user_id=profile.id, role=args.role))
            print(f"Granted {args.role} on '{organization.name}' to profile {profile.id}")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    main()
