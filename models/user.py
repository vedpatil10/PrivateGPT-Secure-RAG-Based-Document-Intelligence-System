"""
User, Organization, and Role models for multi-tenant RBAC.
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, Enum as SAEnum, Text
)
from sqlalchemy.orm import relationship

from models.database import Base


class Role(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Organization(Base):
    """Tenant/organization entity — the root of data isolation."""
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    settings = Column(Text, default="{}")  # JSON org-level settings
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name}>"


class User(Base):
    """User account belonging to an organization."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(SAEnum(Role), default=Role.ANALYST, nullable=False)
    is_active = Column(Boolean, default=True)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")

    def __repr__(self):
        return f"<User {self.email} [{self.role.value}]>"
