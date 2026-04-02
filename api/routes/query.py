"""
Query API routes — REST and WebSocket endpoints for RAG queries.
"""

from fastapi import APIRouter, Depends, Request, WebSocket

from api.websocket import stream_query_websocket
from models.schemas import QueryRequest, QueryResponse
from models.database import get_db_session
from core.dependencies import get_current_user
from services.audit_service import AuditService
from services.rag_pipeline import get_rag_pipeline
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    http_request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Execute a RAG query against the user's document collection."""
    pipeline = get_rag_pipeline()

    result = pipeline.query(
        question=request.question,
        org_id=current_user["org_id"],
        user_role=current_user["role"],
        conversation_id=request.conversation_id,
        top_k=request.top_k,
    )

    await AuditService.log_event(
        db,
        user_id=current_user["user_id"],
        user_email=current_user.get("email"),
        org_id=current_user["org_id"],
        action="query",
        query_text=request.question,
        response_text=result["answer"],
        chunks_used=[
            f"{src['document_name']}:{src.get('page_number') or src.get('section_title') or 'n/a'}"
            for src in result["sources"]
        ],
        source_documents=[src["document_name"] for src in result["sources"]],
        request_id=getattr(http_request.state, "request_id", None),
        ip_address=http_request.client.host if http_request.client else None,
        duration_ms=result["query_time_ms"],
    )

    return QueryResponse(**result)


@router.websocket("/ws")
async def query_stream(websocket: WebSocket):
    """WebSocket endpoint for streaming RAG responses."""
    await stream_query_websocket(websocket)
