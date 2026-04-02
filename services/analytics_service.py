"""
Usage analytics service — tracks query volumes, document usage, performance metrics.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from models.document import Document

logger = logging.getLogger("privategpt.analytics")


class AnalyticsService:
    """Computes usage analytics for tenant dashboards and SaaS billing."""

    @staticmethod
    async def get_usage_stats(org_id: str, db: AsyncSession, days: int = 30) -> dict:
        """Get usage statistics for an organization."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total queries
        query_count = await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.org_id == org_id,
                AuditLog.action == "query",
                AuditLog.created_at >= since,
            )
        )
        total_queries = query_count.scalar() or 0

        # Total documents
        doc_count = await db.execute(
            select(func.count(Document.id)).where(
                Document.org_id == org_id,
            )
        )
        total_documents = doc_count.scalar() or 0

        # Total chunks
        chunk_count = await db.execute(
            select(func.sum(Document.chunk_count)).where(
                Document.org_id == org_id,
            )
        )
        total_chunks = chunk_count.scalar() or 0

        # Average response time
        avg_time = await db.execute(
            select(func.avg(AuditLog.duration_ms)).where(
                AuditLog.org_id == org_id,
                AuditLog.action == "query",
                AuditLog.created_at >= since,
            )
        )
        avg_response_time = round(avg_time.scalar() or 0, 1)

        query_logs_result = await db.execute(
            select(AuditLog).where(
                AuditLog.org_id == org_id,
                AuditLog.action == "query",
                AuditLog.created_at >= since,
            )
        )
        query_logs = list(query_logs_result.scalars().all())

        document_counter = Counter()
        volume_by_day = Counter()
        no_context_queries = 0

        for log in query_logs:
            day_key = log.created_at.date().isoformat()
            volume_by_day[day_key] += 1

            if log.response_text and "don't have enough information in the provided documents" in log.response_text.lower():
                no_context_queries += 1

            if not log.source_documents:
                continue

            try:
                for doc_name in json.loads(log.source_documents):
                    if doc_name:
                        document_counter[doc_name] += 1
            except Exception:
                logger.warning("Failed to parse source_documents for audit log %s", log.id)

        failed_query_rate = round((no_context_queries / total_queries) * 100, 1) if total_queries else 0.0

        return {
            "total_queries": total_queries,
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "avg_response_time_ms": avg_response_time,
            "failed_query_rate": failed_query_rate,
            "no_context_queries": no_context_queries,
            "most_queried_documents": [
                {"document_name": name, "query_count": count}
                for name, count in document_counter.most_common(5)
            ],
            "query_volume_by_day": [
                {"date": day, "queries": count}
                for day, count in sorted(volume_by_day.items())
            ],
            "period_days": days,
        }
