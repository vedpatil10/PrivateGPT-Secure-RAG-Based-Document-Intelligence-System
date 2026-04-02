"""
Async document ingestion pipeline — queues documents for background processing,
tracks status, and supports selective re-indexing on update/delete.
"""

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from sqlalchemy import delete as sql_delete
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import get_settings
from core.security import decrypt_file, encrypt_file
from models.document import (
    Document,
    DocumentChunk,
    DocumentStatus,
    ChunkType,
    AccessLevel,
)
from services.ingestion.loaders import load_document
from services.ingestion.chunker import chunk_document
from services.ingestion.processor import clean_text

logger = logging.getLogger("privategpt.ingestion")

# Thread pool for CPU-bound document parsing
_executor = ThreadPoolExecutor(max_workers=2)


class IngestionPipeline:
    """
    Manages the full document lifecycle:
    upload → parse → chunk → embed → index → queryable
    """

    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._is_running = False

    async def start_background_worker(self):
        """Start the background ingestion worker."""
        if self._is_running:
            return
        self._is_running = True
        asyncio.create_task(self._worker_loop())
        logger.info("Ingestion background worker started")

    async def _worker_loop(self):
        """Continuously process queued documents."""
        while self._is_running:
            try:
                task = await asyncio.wait_for(
                    self._processing_queue.get(),
                    timeout=5.0,
                )
                await self._process_document_task(task)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def queue_document(
        self,
        file_path: str,
        original_filename: str,
        file_size: int,
        org_id: str,
        user_id: str,
        access_level: str = "public",
        db: AsyncSession = None,
    ) -> str:
        """
        Save uploaded file, create DB record, and queue for processing.
        Returns the document ID.
        """
        doc_id = str(uuid.uuid4())

        # Determine file type
        file_ext = Path(original_filename).suffix.lower().lstrip(".")
        dest_path = self._store_uploaded_file(file_path, doc_id, org_id, file_ext)
        file_hash = self._compute_file_hash(dest_path)

        # Create DB record
        if db:
            doc = Document(
                id=doc_id,
                filename=str(dest_path),
                original_filename=original_filename,
                file_type=file_ext,
                file_size=file_size,
                file_hash=file_hash,
                status=DocumentStatus.QUEUED,
                access_level=AccessLevel(access_level),
                org_id=org_id,
                uploaded_by=user_id,
            )
            db.add(doc)
            await db.commit()

        # Queue for background processing
        await self._processing_queue.put({
            "doc_id": doc_id,
            "file_path": str(dest_path),
            "original_filename": original_filename,
            "org_id": org_id,
            "user_id": user_id,
            "access_level": access_level,
        })

        logger.info(f"Document queued: {original_filename} (id={doc_id})")
        return doc_id

    async def process_document_sync(
        self,
        file_path: str,
        original_filename: str,
        org_id: str,
        user_id: str,
        doc_id: str = None,
        access_level: str = "public",
        db: AsyncSession = None,
    ) -> dict:
        """
        Process a document synchronously (for Streamlit direct processing).
        Returns processing results.
        """
        doc_id = doc_id or str(uuid.uuid4())
        file_ext = Path(original_filename).suffix.lower().lstrip(".")
        stored_path, parse_path, temp_decrypted_path = self._prepare_processing_paths(
            file_path=file_path,
            doc_id=doc_id,
            org_id=org_id,
            file_ext=file_ext,
        )
        file_hash = self._compute_file_hash(stored_path)
        file_size = Path(stored_path).stat().st_size

        try:
            if db:
                await self._upsert_document_record(
                    db=db,
                    doc_id=doc_id,
                    stored_path=stored_path,
                    original_filename=original_filename,
                    file_ext=file_ext,
                    file_size=file_size,
                    file_hash=file_hash,
                    org_id=org_id,
                    user_id=user_id,
                    access_level=access_level,
                )

            # 1. Parse the document (CPU-bound, run in thread)
            logger.info(f"Parsing: {original_filename}")
            loop = asyncio.get_event_loop()
            loaded_doc = await loop.run_in_executor(
                _executor, load_document, parse_path
            )

            # 2. Clean text
            cleaned_content = clean_text(loaded_doc.content)
            if not cleaned_content or len(cleaned_content) < 10:
                raise ValueError("Document contains no extractable text")

            # 3. Chunk the document
            chunks = chunk_document(
                cleaned_content,
                loaded_doc.page_contents,
            )

            if not chunks:
                raise ValueError("No chunks produced from document")

            # 4. Generate embeddings
            chunk_texts = [c.content for c in chunks]
            embeddings = await loop.run_in_executor(
                _executor,
                self.embedding_service.encode,
                chunk_texts,
            )

            # 5. Refresh document vectors if this is a re-index/update.
            self.vector_store.remove_vectors_by_doc(org_id, doc_id)

            # 6. Store in FAISS (per-tenant index)
            chunk_ids = self.vector_store.add_vectors(
                org_id=org_id,
                vectors=embeddings,
                metadatas=[{
                    "doc_id": doc_id,
                    "chunk_index": c.chunk_index,
                    "chunk_type": c.chunk_type,
                    "content": c.content,
                    "page_number": c.page_number,
                    "section_title": c.section_title,
                    "filename": original_filename,
                    "access_level": access_level,
                } for c in chunks],
            )

            # 7. Save to database
            if db:
                await db.execute(
                    sql_delete(DocumentChunk).where(DocumentChunk.document_id == doc_id)
                )

                await db.execute(
                    update(Document).where(Document.id == doc_id).values(
                        status=DocumentStatus.INDEXED,
                        chunk_count=len(chunks),
                        page_count=loaded_doc.metadata.get("page_count"),
                        summary=chunks[0].content if chunks[0].chunk_type == "summary" else None,
                    )
                )

                # Create chunk records
                for chunk, chunk_id in zip(chunks, chunk_ids):
                    db_chunk = DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        chunk_index=chunk.chunk_index,
                        chunk_type=ChunkType(chunk.chunk_type),
                        content=chunk.content,
                        content_length=chunk.content_length,
                        page_number=chunk.page_number,
                        section_title=chunk.section_title,
                        embedding_id=chunk_id,
                    )
                    db.add(db_chunk)

                await db.commit()

            # 8. Persist FAISS index
            self.vector_store.save_index(org_id)

            result = {
                "doc_id": doc_id,
                "status": "indexed",
                "chunks": len(chunks),
                "filename": original_filename,
                "stored_path": stored_path,
            }
            logger.info(f"Document indexed: {original_filename} ({len(chunks)} chunks)")
            return result

        except Exception as e:
            logger.error(f"Ingestion failed for {original_filename}: {e}")
            if db:
                await db.execute(
                    update(Document).where(Document.id == doc_id).values(
                        status=DocumentStatus.ERROR,
                        error_message=str(e),
                    )
                )
                await db.commit()
            raise
        finally:
            if temp_decrypted_path and Path(temp_decrypted_path).exists():
                Path(temp_decrypted_path).unlink(missing_ok=True)

    async def _process_document_task(self, task: dict):
        """Process a single queued document task."""
        from models.database import async_session_factory

        async with async_session_factory() as db:
            await self.process_document_sync(
                file_path=task["file_path"],
                original_filename=task["original_filename"],
                org_id=task["org_id"],
                user_id=task["user_id"],
                doc_id=task["doc_id"],
                access_level=task.get("access_level", "public"),
                db=db,
            )

    async def delete_document(
        self,
        doc_id: str,
        org_id: str,
        db: AsyncSession = None,
    ):
        """
        Remove a document and its embeddings from FAISS
        without rebuilding the entire index.
        """
        doc: Optional[Document] = None
        if db:
            result = await db.execute(
                select(Document).where(
                    Document.id == doc_id,
                    Document.org_id == org_id,
                )
            )
            doc = result.scalar_one_or_none()

        # Remove vectors from FAISS by doc_id
        self.vector_store.remove_vectors_by_doc(org_id, doc_id)
        self.vector_store.save_index(org_id)

        # Remove from database
        if db:
            await db.execute(
                sql_delete(DocumentChunk).where(DocumentChunk.document_id == doc_id)
            )
            await db.execute(
                sql_delete(Document).where(Document.id == doc_id)
            )
            await db.commit()

        if doc and doc.filename and Path(doc.filename).exists():
            Path(doc.filename).unlink(missing_ok=True)

        logger.info(f"Document deleted: {doc_id}")

    @staticmethod
    def _compute_file_hash(file_path: str) -> str:
        """Compute SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _store_uploaded_file(
        file_path: str,
        doc_id: str,
        org_id: str,
        file_ext: str,
    ) -> str:
        """Encrypt and store an uploaded file in tenant-scoped persistent storage."""
        settings = get_settings()
        org_upload_dir = Path(settings.upload_dir) / org_id
        org_upload_dir.mkdir(parents=True, exist_ok=True)
        dest_path = org_upload_dir / f"{doc_id}.{file_ext}.enc"

        encrypted_bytes = encrypt_file(Path(file_path).read_bytes())
        Path(dest_path).write_bytes(encrypted_bytes)
        return str(dest_path)

    @staticmethod
    def _prepare_processing_paths(
        file_path: str,
        doc_id: str,
        org_id: str,
        file_ext: str,
    ) -> tuple[str, str, Optional[str]]:
        """Return persisted encrypted path and a temporary decrypted parse path."""
        source_path = Path(file_path)
        is_encrypted_upload = source_path.suffix == ".enc"

        if is_encrypted_upload:
            stored_path = str(source_path)
        else:
            stored_path = IngestionPipeline._store_uploaded_file(
                file_path=file_path,
                doc_id=doc_id,
                org_id=org_id,
                file_ext=file_ext,
            )

        encrypted_bytes = Path(stored_path).read_bytes()
        decrypted_bytes = decrypt_file(encrypted_bytes)

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(decrypted_bytes)
            temp_path = tmp.name

        return stored_path, temp_path, temp_path

    @staticmethod
    async def _upsert_document_record(
        db: AsyncSession,
        doc_id: str,
        stored_path: str,
        original_filename: str,
        file_ext: str,
        file_size: int,
        file_hash: str,
        org_id: str,
        user_id: str,
        access_level: str,
    ) -> None:
        """Create or refresh the document row before indexing."""
        result = await db.execute(select(Document).where(Document.id == doc_id))
        existing = result.scalar_one_or_none()
        normalized_access = AccessLevel(access_level)

        if existing is None:
            db.add(
                Document(
                    id=doc_id,
                    filename=stored_path,
                    original_filename=original_filename,
                    file_type=file_ext,
                    file_size=file_size,
                    file_hash=file_hash,
                    status=DocumentStatus.PROCESSING,
                    access_level=normalized_access,
                    org_id=org_id,
                    uploaded_by=user_id,
                )
            )
        else:
            await db.execute(
                update(Document)
                .where(Document.id == doc_id)
                .values(
                    filename=stored_path,
                    original_filename=original_filename,
                    file_type=file_ext,
                    file_size=file_size,
                    file_hash=file_hash,
                    status=DocumentStatus.PROCESSING,
                    access_level=normalized_access,
                    error_message=None,
                )
            )

        await db.commit()


_instance: Optional[IngestionPipeline] = None


def get_ingestion_pipeline() -> IngestionPipeline:
    """Get or create the shared ingestion pipeline singleton."""
    global _instance
    if _instance is None:
        from services.embedding_service import get_embedding_service
        from services.vector_store import get_vector_store

        embedding_service = get_embedding_service()
        vector_store = get_vector_store(dimension=embedding_service.dimension)
        _instance = IngestionPipeline(embedding_service, vector_store)
    return _instance
