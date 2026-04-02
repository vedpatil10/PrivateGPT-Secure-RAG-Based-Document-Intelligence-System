"""
Audit logging helpers for compliance-friendly event tracking.
"""

import json
import logging
from typing import Any, Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog

logger = logging.getLogger("privategpt.audit")


class AuditService:
    """Persists audit trail entries for auth, document, and query activity."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        *,
        user_id: str,
        org_id: str,
        action: str,
        user_email: Optional[str] = None,
        query_text: Optional[str] = None,
        response_text: Optional[str] = None,
        chunks_used: Optional[Iterable[str]] = None,
        source_documents: Optional[Iterable[str]] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Create a single audit-log record."""
        record = AuditLog(
            user_id=user_id,
            user_email=user_email,
            org_id=org_id,
            action=action,
            query_text=query_text,
            response_text=response_text,
            chunks_used=json.dumps(list(chunks_used or [])),
            source_documents=json.dumps(list(source_documents or [])),
            request_id=request_id,
            ip_address=ip_address,
            duration_ms=duration_ms,
        )
        db.add(record)
        await db.commit()

        logger.info(
            "Audit event stored: action=%s org_id=%s user_id=%s",
            action,
            org_id,
            user_id,
        )
