"""
Audit log model for compliance tracking.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, Text, Integer

from models.database import Base


class AuditLog(Base):
    """Immutable audit trail for every query and response."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Who
    user_id = Column(String(36), nullable=False, index=True)
    user_email = Column(String(255), nullable=True)
    org_id = Column(String(36), nullable=False, index=True)

    # What
    action = Column(String(50), nullable=False)  # query, upload, delete, login, etc.
    query_text = Column(Text, nullable=True)
    response_text = Column(Text, nullable=True)

    # Provenance — which chunks were used
    chunks_used = Column(Text, nullable=True)  # JSON list of chunk IDs
    source_documents = Column(Text, nullable=True)  # JSON list of doc filenames

    # Context
    request_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # When
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_email} at {self.created_at}>"
