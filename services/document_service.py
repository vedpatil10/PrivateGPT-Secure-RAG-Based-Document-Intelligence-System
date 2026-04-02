"""
Document service layer for CRUD and tenant-safe document lookups.
"""

from typing import Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.document import Document, DocumentChunk


class DocumentService:
    """Encapsulates common document queries and mutations."""

    @staticmethod
    async def list_documents(org_id: str, db: AsyncSession) -> list[Document]:
        result = await db.execute(
            select(Document)
            .where(Document.org_id == org_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_document(
        doc_id: str,
        org_id: str,
        db: AsyncSession,
    ) -> Optional[Document]:
        result = await db.execute(
            select(Document).where(
                Document.id == doc_id,
                Document.org_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_document_status(
        doc_id: str,
        org_id: str,
        db: AsyncSession,
    ) -> Optional[dict]:
        document = await DocumentService.get_document(doc_id, org_id, db)
        if document is None:
            return None

        return {
            "id": document.id,
            "status": document.status.value,
            "chunk_count": document.chunk_count,
            "error_message": document.error_message,
            "updated_at": document.updated_at,
        }

    @staticmethod
    async def hard_delete_document(
        doc_id: str,
        org_id: str,
        db: AsyncSession,
    ) -> bool:
        document = await DocumentService.get_document(doc_id, org_id, db)
        if document is None:
            return False

        await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))
        await db.execute(sql_delete(Document).where(Document.id == doc_id))
        await db.commit()
        return True
