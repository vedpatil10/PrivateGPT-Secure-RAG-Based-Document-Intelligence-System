"""
End-to-end RAG pipeline — orchestrates retrieval, prompt construction,
LLM generation, and audit logging. Supports streaming and conversation memory.
"""

import logging
import time
import uuid
from typing import List, Optional, Generator, Dict

from config.settings import get_settings
from services.retrieval_service import get_retrieval_service, RetrievalResult
from services.llm_service import get_llm_service

logger = logging.getLogger("privategpt.rag")


# ── Prompt Templates ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are PrivateGPT, an intelligent document assistant. Your job is to answer questions accurately based ONLY on the provided context documents. 

Rules:
1. Answer based ONLY on the provided context. Do NOT use prior knowledge.
2. If the context does not contain enough information to answer, say "I don't have enough information in the provided documents to answer this question."
3. When citing information, reference the source document name and page/section.
4. Be concise, accurate, and professional.
5. If multiple documents provide relevant information, synthesize them into a coherent answer."""

CONTEXT_TEMPLATE = """
--- Source: {filename}{page_info}{section_info} ---
{content}
"""

RAG_PROMPT_TEMPLATE = """<s>[INST] <<SYS>>
{system_prompt}
<</SYS>>

CONTEXT DOCUMENTS:
{context}

{conversation_history}USER QUESTION: {question} [/INST]"""

# Alternative template for non-LLaMA models
GENERIC_PROMPT_TEMPLATE = """### System:
{system_prompt}

### Context Documents:
{context}

{conversation_history}### User Question:
{question}

### Assistant:"""


class ConversationMemory:
    """Sliding window conversation memory."""

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self._conversations: Dict[str, List[Dict]] = {}

    def get_history(self, conversation_id: str) -> List[Dict]:
        return self._conversations.get(conversation_id, [])

    def add_turn(self, conversation_id: str, question: str, answer: str):
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []

        self._conversations[conversation_id].append({
            "question": question,
            "answer": answer,
        })

        # Sliding window — keep only last N turns
        if len(self._conversations[conversation_id]) > self.max_turns:
            self._conversations[conversation_id] = \
                self._conversations[conversation_id][-self.max_turns:]

    def format_history(self, conversation_id: str) -> str:
        history = self.get_history(conversation_id)
        if not history:
            return ""

        formatted = "CONVERSATION HISTORY:\n"
        for turn in history:
            formatted += f"User: {turn['question']}\n"
            formatted += f"Assistant: {turn['answer']}\n\n"
        return formatted

    def clear(self, conversation_id: str):
        self._conversations.pop(conversation_id, None)


class RAGPipeline:
    """
    End-to-end RAG orchestration:
    1. Retrieve relevant chunks
    2. Construct grounded prompt with context + conversation history
    3. Generate response via LLM
    4. Return answer with source citations
    """

    def __init__(self):
        self.memory = ConversationMemory()

    def query(
        self,
        question: str,
        org_id: str,
        user_role: str = "analyst",
        conversation_id: str = None,
        top_k: int = None,
    ) -> dict:
        """
        Execute a complete RAG query. Returns answer + sources.
        """
        start_time = time.time()
        conversation_id = conversation_id or str(uuid.uuid4())

        # 1. Retrieve relevant chunks
        retrieval_service = get_retrieval_service()
        results = retrieval_service.retrieve(
            query=question,
            org_id=org_id,
            user_role=user_role,
            top_n=top_k,
        )

        if not results:
            answer = (
                "I don't have enough information in the provided documents "
                "to answer this question."
            )
            self.memory.add_turn(conversation_id, question, answer)
            return {
                "answer": answer,
                "sources": [],
                "conversation_id": conversation_id,
                "query_time_ms": int((time.time() - start_time) * 1000),
                "chunks_used": 0,
            }

        # 2. Build context from retrieved chunks
        context = self._build_context(results)

        # 3. Get conversation history
        history = self.memory.format_history(conversation_id)

        # 4. Construct prompt
        prompt = self._build_prompt(question, context, history)

        # 5. Generate response
        settings = get_settings()
        llm = get_llm_service()

        answer = llm.generate(
            prompt=prompt,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )

        # 6. Update conversation memory
        self.memory.add_turn(conversation_id, question, answer)

        # 7. Build response
        duration_ms = int((time.time() - start_time) * 1000)

        sources = [
            {
                "document_name": r.filename,
                "chunk_content": r.content[:300] + "..." if len(r.content) > 300 else r.content,
                "page_number": r.page_number,
                "section_title": r.section_title,
                "relevance_score": round(r.score, 4),
            }
            for r in results
        ]

        response = {
            "answer": answer,
            "sources": sources,
            "conversation_id": conversation_id,
            "query_time_ms": duration_ms,
            "chunks_used": len(results),
        }

        logger.info(
            f"RAG query completed in {duration_ms}ms. "
            f"Chunks used: {len(results)}. "
            f"Q: {question[:50]}..."
        )

        return response

    def query_stream(
        self,
        question: str,
        org_id: str,
        user_role: str = "analyst",
        conversation_id: str = None,
        top_k: int = None,
    ) -> Generator[dict, None, None]:
        """
        Stream a RAG query response token by token.
        Yields dicts with type="token" or type="sources".
        """
        start_time = time.time()
        conversation_id = conversation_id or str(uuid.uuid4())

        # 1. Retrieve
        retrieval_service = get_retrieval_service()
        results = retrieval_service.retrieve(
            query=question,
            org_id=org_id,
            user_role=user_role,
            top_n=top_k,
        )

        if not results:
            answer = (
                "I don't have enough information in the provided documents "
                "to answer this question."
            )
            self.memory.add_turn(conversation_id, question, answer)
            yield {"type": "sources", "data": []}
            yield {"type": "token", "data": answer}
            yield {
                "type": "done",
                "data": {
                    "conversation_id": conversation_id,
                    "chunks_used": 0,
                    "query_time_ms": int((time.time() - start_time) * 1000),
                },
            }
            return

        # 2. Build prompt
        context = self._build_context(results)
        history = self.memory.format_history(conversation_id)
        prompt = self._build_prompt(question, context, history)

        # 3. Yield source info first
        sources = [
            {
                "document_name": r.filename,
                "chunk_content": r.content[:300] + "..." if len(r.content) > 300 else r.content,
                "page_number": r.page_number,
                "section_title": r.section_title,
                "relevance_score": round(r.score, 4),
            }
            for r in results
        ]
        yield {"type": "sources", "data": sources}

        # 4. Stream tokens
        settings = get_settings()
        llm = get_llm_service()
        full_answer = ""

        for token in llm.stream(
            prompt=prompt,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        ):
            full_answer += token
            yield {"type": "token", "data": token}

        # 5. Update memory
        self.memory.add_turn(conversation_id, question, full_answer)

        # 6. Yield completion
        yield {
            "type": "done",
            "data": {
                "conversation_id": conversation_id,
                "chunks_used": len(results),
                "query_time_ms": int((time.time() - start_time) * 1000),
            },
        }

    def _build_context(self, results: List[RetrievalResult]) -> str:
        """Build the context section from retrieval results."""
        if not results:
            return "[No relevant documents found]"

        context_parts = []
        for r in results:
            page_info = f" | Page {r.page_number}" if r.page_number else ""
            section_info = f" | Section: {r.section_title}" if r.section_title else ""

            context_parts.append(CONTEXT_TEMPLATE.format(
                filename=r.filename,
                page_info=page_info,
                section_info=section_info,
                content=r.content,
            ))

        return "\n".join(context_parts)

    def _build_prompt(self, question: str, context: str, history: str = "") -> str:
        """Construct the full prompt for the LLM."""
        settings = get_settings()

        # Use LLaMA-2 chat template for llama_cpp provider
        if settings.llm_provider == "llama_cpp":
            template = RAG_PROMPT_TEMPLATE
        else:
            template = GENERIC_PROMPT_TEMPLATE

        prompt = template.format(
            system_prompt=SYSTEM_PROMPT,
            context=context,
            conversation_history=history,
            question=question,
        )

        return prompt


# ── Singleton ────────────────────────────────────────────────────

_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the singleton RAG pipeline."""
    global _instance
    if _instance is None:
        _instance = RAGPipeline()
    return _instance
