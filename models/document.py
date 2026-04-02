"""
Document and DocumentChunk models for tracking ingested files.
"""

import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Integer, Text, Enum as SAEnum, BigInteger
)
from sqlalchemy.orm import relationship

from models.database import Base


class DocumentStatus(str, enum.Enum):
    """Document processing status."""
    QUEUED = "queued"
    PROCESSING = "processing"
    INDEXED = "indexed"
    ERROR = "error"


class ChunkType(str, enum.Enum):
    """Type of document chunk."""
    SUMMARY = "summary"
    DETAIL = "detail"


class AccessLevel(str, enum.Enum):
    """Document access level for RBAC."""
    PUBLIC = "public"          # All org users can access
    INTERNAL = "internal"      # Analysts and above
    CONFIDENTIAL = "confidential"  # Managers and above
    RESTRICTED = "restricted"  # Admins only


class Document(Base):
    """Metadata for an uploaded document."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, xlsx, etc.
    file_size = Column(BigInteger, default=0)
    file_hash = Column(String(64), nullable=True)  # SHA-256 for deduplication

    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.QUEUED)
    access_level = Column(SAEnum(AccessLevel), default=AccessLevel.PUBLIC)
    error_message = Column(Text, nullable=True)

    # Metadata
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    summary = Column(Text, nullable=True)  # Auto-generated document summary

    # Tenant isolation
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organization = relationship("Organization", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.original_filename} [{self.status.value}]>"


class DocumentChunk(Base):
    """Individual chunk of a document with embedding reference."""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    chunk_type = Column(SAEnum(ChunkType), default=ChunkType.DETAIL)

    content = Column(Text, nullable=False)
    content_length = Column(Integer, default=0)

    # Source tracking for citations
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(500), nullable=True)

    # Vector reference
    embedding_id = Column(String(100), nullable=True)  # ID in FAISS index

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<Chunk {self.document_id}:{self.chunk_index} [{self.chunk_type.value}]>"
