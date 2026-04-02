"""
Conversational Q&A page with streaming answers and citations.
"""

import os
import sys
import uuid

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from streamlit_app.components.chat_message import render_chat_message
from streamlit_app.utils import run_async

st.set_page_config(page_title="PrivateGPT - Chat", page_icon="C", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page.")
    st.stop()

st.markdown(
    """
<style>
    .stApp { background: #0a0a0f !important; color: #e8e8f0 !important; }
    .chat-user-msg {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px 16px 4px 16px;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        color: #e8e8f0;
    }
    .chat-ai-msg {
        background: #1a1a2e;
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 16px 16px 16px 4px;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        color: #e8e8f0;
        line-height: 1.65;
    }
    .source-item {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.12);
        border-radius: 8px;
        padding: 0.6rem 0.85rem;
        margin: 0.35rem 0;
        font-size: 0.82rem;
        color: #9ca3af;
    }
    .source-filename {
        color: #3b82f6;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .query-time {
        color: #6b7280;
        font-size: 0.75rem;
        text-align: right;
        margin-top: 0.3rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())

st.markdown(
    """
<h1 style="font-size: 2rem;">Document Chat</h1>
<p style="color: #9ca3af;">Ask questions about your documents. Answers include source citations.</p>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Chat Controls")
    if st.button("New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    top_k = st.slider("Number of sources", 1, 10, 5)
    st.divider()
    st.markdown("**Conversation ID**")
    st.code(st.session_state.conversation_id[:8] + "...", language=None)

chat_container = st.container()
with chat_container:
    if not st.session_state.messages:
        st.markdown(
            """
        <div style="text-align: center; padding: 4rem 2rem; color: #6b7280;">
            <p style="font-size: 3rem; margin-bottom: 0.5rem;">Chat Ready</p>
            <p style="font-size: 1rem; color: #9ca3af;">Ask anything about your uploaded documents.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        for msg in st.session_state.messages:
            render_chat_message(st, msg)

question = st.chat_input("Ask a question about your documents...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})

    with chat_container:
        render_chat_message(st, {"role": "user", "content": question})

    with st.spinner("Searching documents and generating answer..."):
        try:
            from services.rag_pipeline import get_rag_pipeline

            pipeline = get_rag_pipeline()
            streamed_answer_parts = []
            sources = []
            query_time_ms = 0
            assistant_placeholder = st.empty()

            for chunk in pipeline.query_stream(
                question=question,
                org_id=st.session_state.org_id,
                user_role=st.session_state.user.get("role", "analyst"),
                conversation_id=st.session_state.conversation_id,
                top_k=top_k,
            ):
                if chunk["type"] == "sources":
                    sources = chunk["data"]
                elif chunk["type"] == "token":
                    streamed_answer_parts.append(chunk["data"])
                    assistant_placeholder.markdown(
                        f'<div class="chat-ai-msg">Assistant {"".join(streamed_answer_parts)}</div>',
                        unsafe_allow_html=True,
                    )
                elif chunk["type"] == "done":
                    query_time_ms = chunk["data"].get("query_time_ms", 0)

            final_answer = "".join(streamed_answer_parts)

            async def log_query():
                from models.database import async_session_factory, init_db
                from services.audit_service import AuditService

                await init_db()
                async with async_session_factory() as db:
                    await AuditService.log_event(
                        db,
                        user_id=st.session_state.user["id"],
                        user_email=st.session_state.user.get("email"),
                        org_id=st.session_state.org_id,
                        action="query",
                        query_text=question,
                        response_text=final_answer,
                        chunks_used=[
                            f"{src['document_name']}:{src.get('page_number') or src.get('section_title') or 'n/a'}"
                            for src in sources
                        ],
                        source_documents=[src["document_name"] for src in sources],
                        duration_ms=query_time_ms,
                    )

            run_async(log_query())

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": final_answer,
                    "sources": sources,
                    "query_time_ms": query_time_ms,
                }
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Error: {exc}")
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Error: {exc}"}
            )
