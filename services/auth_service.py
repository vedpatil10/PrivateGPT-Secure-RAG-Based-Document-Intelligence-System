"""
Authentication service — registration, login, user management.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password, verify_password, create_access_token
from models.user import User, Organization, Role

logger = logging.getLogger("privategpt.auth")


class AuthService:
    """Handles user authentication and organization management."""

    @staticmethod
    def _build_auth_payload(user: User) -> dict:
        """Build the standard JWT payload for a user."""
        return {
            "sub": user.id,
            "email": user.email,
            "org_id": user.org_id,
            "role": user.role.value,
        }

    @staticmethod
    def _build_auth_response(user: User) -> dict:
        """Build the standard login/register response payload."""
        token = create_access_token(AuthService._build_auth_payload(user))
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "org_id": user.org_id,
                "is_active": user.is_active,
            },
        }

    @staticmethod
    async def register(
        org_name: str,
        email: str,
        password: str,
        full_name: str,
        db: AsyncSession,
    ) -> dict:
        """Register a new organization with an admin user."""
        # Check if email already exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Create organization
        slug = org_name.lower().replace(" ", "-").replace(".", "")
        org = Organization(name=org_name, slug=slug)
        db.add(org)
        await db.flush()

        # Create admin user
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=Role.ADMIN,
            org_id=org.id,
        )
        db.add(user)
        await db.commit()

        logger.info(f"New org registered: {org_name} (admin: {email})")

        return AuthService._build_auth_response(user)

    @staticmethod
    async def login(email: str, password: str, db: AsyncSession) -> dict:
        """Authenticate a user and return a JWT token."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"User logged in: {email}")

        return AuthService._build_auth_response(user)

    @staticmethod
    async def invite_user(
        email: str,
        full_name: str,
        role: str,
        org_id: str,
        db: AsyncSession,
    ) -> dict:
        """Invite a user to an organization with a specified role."""
        # Check if email exists
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Default password (user should change)
        default_password = "changeme123!"

        user = User(
            email=email,
            hashed_password=hash_password(default_password),
            full_name=full_name,
            role=Role(role),
            org_id=org_id,
        )
        db.add(user)
        await db.commit()

        logger.info(f"User invited: {email} as {role} to org {org_id}")

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "org_id": org_id,
            "temporary_password": default_password,
        }

    @staticmethod
    async def get_user_by_id(user_id: str, db: AsyncSession) -> Optional[User]:
        """Get a user by their ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def refresh_token(user_id: str, db: AsyncSession) -> dict:
        """Issue a fresh access token for an authenticated user."""
        user = await AuthService.get_user_by_id(user_id, db)
        if user is None or not user.is_active:
            raise ValueError("User not found or inactive")

        token = create_access_token(AuthService._build_auth_payload(user))
        return {
            "access_token": token,
            "token_type": "bearer",
        }
