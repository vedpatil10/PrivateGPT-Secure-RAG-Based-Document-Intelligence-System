"""
Document management API routes — upload, list, delete, status.
"""

import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db_session
from models.schemas import DocumentListResponse, DocumentResponse, DocumentStatusResponse
from core.dependencies import get_current_user, require_role
from services.audit_service import AuditService
from services.document_service import DocumentService
from services.ingestion.pipeline import get_ingestion_pipeline

router = APIRouter()


@router.post("/upload", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    access_level: str = Form("public"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Upload and queue a document for background processing."""
    # Save to temp file
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        pipeline = get_ingestion_pipeline()
        doc_id = await pipeline.queue_document(
            file_path=tmp_path,
            original_filename=file.filename,
            file_size=len(content),
            org_id=current_user["org_id"],
            user_id=current_user["user_id"],
            access_level=access_level,
            db=db,
        )
        await AuditService.log_event(
            db,
            user_id=current_user["user_id"],
            user_email=current_user.get("email"),
            org_id=current_user["org_id"],
            action="upload",
            response_text=f"Uploaded {file.filename}",
            source_documents=[file.filename],
        )
        return {
            "doc_id": doc_id,
            "status": "queued",
            "filename": file.filename,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}",
        )
    finally:
        os.unlink(tmp_path)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """List all documents for the current tenant."""
    docs = await DocumentService.list_documents(current_user["org_id"], db)

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get document details."""
    doc = await DocumentService.get_document(doc_id, current_user["org_id"], db)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get("/{doc_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Get ingestion status for a document."""
    status_payload = await DocumentService.get_document_status(
        doc_id,
        current_user["org_id"],
        db,
    )
    if not status_payload:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(**status_payload)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete a document and its embeddings."""
    doc = await DocumentService.get_document(doc_id, current_user["org_id"], db)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    pipeline = get_ingestion_pipeline()
    await pipeline.delete_document(
        doc_id=doc_id,
        org_id=current_user["org_id"],
        db=db,
    )
    await AuditService.log_event(
        db,
        user_id=current_user["user_id"],
        user_email=current_user.get("email"),
        org_id=current_user["org_id"],
        action="delete",
        response_text=f"Deleted {doc.original_filename}",
        source_documents=[doc.original_filename],
    )
    return {"status": "deleted", "doc_id": doc_id}
