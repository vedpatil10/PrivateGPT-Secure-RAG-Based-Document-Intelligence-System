"""
WebSocket helpers for authenticated streaming query responses.
"""

import json

from fastapi import WebSocket, WebSocketDisconnect

from core.security import decode_access_token
from models.database import async_session_factory
from services.audit_service import AuditService
from services.rag_pipeline import get_rag_pipeline


def _extract_token(websocket: WebSocket) -> str | None:
    """Read a bearer token from query params or headers."""
    token = websocket.query_params.get("token")
    if token:
        return token

    auth_header = websocket.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None


async def stream_query_websocket(websocket: WebSocket):
    """Authenticated WebSocket handler for token streaming."""
    token = _extract_token(websocket)
    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return

    try:
        claims = decode_access_token(token)
    except ValueError:
        await websocket.close(code=4401, reason="Invalid token")
        return

    await websocket.accept()

    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            question = payload.get("question", "").strip()
            conversation_id = payload.get("conversation_id")

            if not question:
                await websocket.send_json({"type": "error", "data": "Missing question"})
                continue

            pipeline = get_rag_pipeline()
            streamed_answer_parts = []
            sources = []

            for chunk in pipeline.query_stream(
                question=question,
                org_id=claims.get("org_id", ""),
                user_role=claims.get("role", "analyst"),
                conversation_id=conversation_id,
                top_k=payload.get("top_k"),
            ):
                if chunk["type"] == "sources":
                    sources = chunk["data"]
                elif chunk["type"] == "token":
                    streamed_answer_parts.append(chunk["data"])

                await websocket.send_json(chunk)

            async with async_session_factory() as db:
                await AuditService.log_event(
                    db,
                    user_id=claims.get("sub", ""),
                    user_email=claims.get("email"),
                    org_id=claims.get("org_id", ""),
                    action="query",
                    query_text=question,
                    response_text="".join(streamed_answer_parts),
                    chunks_used=[
                        f"{src['document_name']}:{src.get('page_number') or src.get('section_title') or 'n/a'}"
                        for src in sources
                    ],
                    source_documents=[src["document_name"] for src in sources],
                )
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.send_json({"type": "error", "data": str(exc)})
