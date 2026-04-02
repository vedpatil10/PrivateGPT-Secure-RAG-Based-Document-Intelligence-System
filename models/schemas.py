"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ── Auth Schemas ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    org_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class InviteRequest(BaseModel):
    email: str
    full_name: str
    role: str = "analyst"


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User Schemas ─────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    org_id: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Document Schemas ─────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    access_level: str
    chunk_count: int
    summary: Optional[str] = None
    created_at: datetime
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int


class DocumentStatusResponse(BaseModel):
    id: str
    status: str
    chunk_count: int
    error_message: Optional[str] = None
    updated_at: datetime


# ── Query Schemas ────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    top_k: Optional[int] = Field(default=5, ge=1, le=20)


class SourceChunk(BaseModel):
    document_name: str
    chunk_content: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]
    conversation_id: str
    query_time_ms: int


# ── Analytics Schemas ────────────────────────────────────────────

class UsageStats(BaseModel):
    total_queries: int
    total_documents: int
    total_chunks: int
    avg_response_time_ms: float
    failed_query_rate: float
    no_context_queries: int
    most_queried_documents: List[dict]
    query_volume_by_day: List[dict]


class UpdateUserRoleRequest(BaseModel):
    role: str = Field(..., min_length=4, max_length=20)


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


# Forward reference resolution
TokenResponse.model_rebuild()
