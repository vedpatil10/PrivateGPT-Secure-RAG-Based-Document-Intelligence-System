"""
Multi-stage retrieval service — FAISS search → RBAC filtering → cross-encoder reranking.
"""

import logging
from typing import List, Dict, Tuple, Optional

import numpy as np

from config.settings import get_settings
from services.embedding_service import get_embedding_service
from services.vector_store import get_vector_store
from models.user import Role
from models.document import AccessLevel

logger = logging.getLogger("privategpt.retrieval")


# ── Access Level Mapping ─────────────────────────────────────────

ROLE_ACCESS_MAP = {
    Role.ADMIN.value: [
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.CONFIDENTIAL.value,
        AccessLevel.RESTRICTED.value,
    ],
    Role.MANAGER.value: [
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.CONFIDENTIAL.value,
    ],
    Role.ANALYST.value: [
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
    ],
    Role.VIEWER.value: [
        AccessLevel.PUBLIC.value,
    ],
}


class RetrievalResult:
    """A single retrieval result with metadata and relevance score."""

    def __init__(
        self,
        content: str,
        score: float,
        doc_id: str,
        filename: str,
        chunk_type: str = "detail",
        page_number: int = None,
        section_title: str = None,
    ):
        self.content = content
        self.score = score
        self.doc_id = doc_id
        self.filename = filename
        self.chunk_type = chunk_type
        self.page_number = page_number
        self.section_title = section_title

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "score": self.score,
            "doc_id": self.doc_id,
            "filename": self.filename,
            "chunk_type": self.chunk_type,
            "page_number": self.page_number,
            "section_title": self.section_title,
        }


class RetrievalService:
    """
    Multi-stage retrieval pipeline:
    1. Embed query → FAISS search (top_k candidates)
    2. RBAC filtering (remove unauthorized chunks)
    3. Cross-encoder reranking (semantic relevance scoring)
    4. Return top_n results
    """

    def __init__(self):
        self._reranker = None

    @property
    def reranker(self):
        """Lazy-load the cross-encoder reranker model."""
        if self._reranker is None:
            settings = get_settings()
            if settings.enable_reranking:
                self._load_reranker()
        return self._reranker

    def _load_reranker(self):
        """Load the cross-encoder model for reranking."""
        from sentence_transformers import CrossEncoder

        settings = get_settings()
        logger.info(f"Loading reranker: {settings.reranker_model}")
        self._reranker = CrossEncoder(
            settings.reranker_model,
            max_length=512,
        )
        logger.info("Reranker loaded")

    def retrieve(
        self,
        query: str,
        org_id: str,
        user_role: str = "analyst",
        top_k: int = None,
        top_n: int = None,
    ) -> List[RetrievalResult]:
        """
        Full retrieval pipeline: embed → search → filter → rerank → return.
        """
        settings = get_settings()
        top_k = top_k or settings.retrieval_top_k
        top_n = top_n or settings.retrieval_top_n

        # 1. Embed the query
        embedding_service = get_embedding_service()
        query_vector = embedding_service.encode_query(query)

        # 2. Search FAISS with access filtering
        access_filter = ROLE_ACCESS_MAP.get(user_role, [AccessLevel.PUBLIC.value])
        vector_store = get_vector_store(dimension=embedding_service.dimension)

        raw_results = vector_store.search(
            org_id=org_id,
            query_vector=query_vector,
            top_k=top_k,
            access_filter=access_filter,
        )

        if not raw_results:
            logger.info(f"No results found for query: {query[:50]}...")
            return []

        # 3. Convert to RetrievalResult objects
        candidates = []
        for meta, score in raw_results:
            candidates.append(RetrievalResult(
                content=meta.get("content", ""),
                score=score,
                doc_id=meta.get("doc_id", ""),
                filename=meta.get("filename", ""),
                chunk_type=meta.get("chunk_type", "detail"),
                page_number=meta.get("page_number"),
                section_title=meta.get("section_title"),
            ))

        # 4. Rerank with cross-encoder (if enabled)
        if settings.enable_reranking and self.reranker is not None:
            candidates = self._rerank(query, candidates)

        # 5. Return top_n
        results = candidates[:top_n]

        logger.info(
            f"Retrieved {len(results)} chunks for query: {query[:50]}... "
            f"(from {len(raw_results)} candidates)"
        )

        return results

    def _rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
    ) -> List[RetrievalResult]:
        """
        Rerank candidates using cross-encoder.
        Scores each (query, chunk) pair for true semantic relevance.
        """
        if not candidates:
            return candidates

        # Create query-document pairs for cross-encoder
        pairs = [(query, c.content) for c in candidates]

        # Score with cross-encoder
        scores = self.reranker.predict(pairs)

        # Update scores and sort
        for candidate, score in zip(candidates, scores):
            candidate.score = float(score)

        candidates.sort(key=lambda x: x.score, reverse=True)

        logger.info(
            f"Reranked {len(candidates)} candidates. "
            f"Top score: {candidates[0].score:.4f}"
        )

        return candidates


# ── Singleton ────────────────────────────────────────────────────

_instance: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get or create the singleton retrieval service."""
    global _instance
    if _instance is None:
        _instance = RetrievalService()
    return _instance
