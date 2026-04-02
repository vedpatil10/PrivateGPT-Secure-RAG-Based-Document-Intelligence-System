"""
Create an admin user for an existing organization.
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from models.database import async_session_factory, init_db
from models.user import Organization, Role, User
from core.security import hash_password


async def main():
    parser = argparse.ArgumentParser(description="Create an admin user for PrivateGPT.")
    parser.add_argument("--org-slug", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    await init_db()

    async with async_session_factory() as db:
        org_result = await db.execute(
            select(Organization).where(Organization.slug == args.org_slug)
        )
        org = org_result.scalar_one_or_none()
        if org is None:
            raise SystemExit(f"Organization not found: {args.org_slug}")

        user_result = await db.execute(select(User).where(User.email == args.email))
        if user_result.scalar_one_or_none():
            raise SystemExit(f"User already exists: {args.email}")

        user = User(
            email=args.email,
            hashed_password=hash_password(args.password),
            full_name=args.full_name,
            role=Role.ADMIN,
            org_id=org.id,
        )
        db.add(user)
        await db.commit()
        print(f"Created admin user {args.email} for {org.slug}")


if __name__ == "__main__":
    asyncio.run(main())
