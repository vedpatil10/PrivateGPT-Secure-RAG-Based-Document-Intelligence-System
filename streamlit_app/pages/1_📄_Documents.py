"""
📄 Documents — Upload, manage, and track document ingestion status.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import tempfile
from pathlib import Path

from streamlit_app.components.document_card import render_document_row
from streamlit_app.utils import run_async

st.set_page_config(page_title="PrivateGPT — Documents", page_icon="📄", layout="wide")

# ── Auth Guard ───────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.warning("🔒 Please log in from the main page.")
    st.stop()

# ── Inject shared CSS ────────────────────────────────────────────
# Load the CSS from main app
css_path = Path(__file__).parent.parent / "app.py"


st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp { background: #0a0a0f !important; font-family: 'Inter', sans-serif !important; }
    h1 { background: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800 !important; }
    .stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important; }
    .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important; }
    [data-testid="stFileUploader"] { border: 2px dashed rgba(99, 102, 241, 0.3) !important; border-radius: 12px !important; }
    [data-testid="stSidebar"] { background: #12121a !important; border-right: 1px solid rgba(99, 102, 241, 0.15) !important; }
    .doc-card { background: #1a1a2e; border: 1px solid rgba(99, 102, 241, 0.15); border-radius: 12px; padding: 1rem; margin: 0.5rem 0; transition: all 0.3s ease; }
    .doc-card:hover { border-color: rgba(99, 102, 241, 0.3); transform: translateY(-1px); }
    .badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.7rem; font-weight: 600; text-transform: uppercase; }
    .badge-success { background: rgba(16, 185, 129, 0.15); color: #10b981; }
    .badge-warning { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
    .badge-error { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
    .badge-info { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
</style>
""", unsafe_allow_html=True)


# ── Initialize Services ─────────────────────────────────────────

def get_services():
    """Initialize and cache services."""
    from services.embedding_service import get_embedding_service
    from services.vector_store import get_vector_store
    from services.ingestion.pipeline import IngestionPipeline

    emb = get_embedding_service()
    vs = get_vector_store(dimension=emb.dimension)
    pipeline = IngestionPipeline(emb, vs)
    return emb, vs, pipeline



# ── Supported Formats ────────────────────────────────────────────

SUPPORTED_FORMATS = [
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "csv", "txt", "md", "msg", "eml",
    "png", "jpg", "jpeg", "tiff", "bmp", "webp",
]


# ── Page Content ─────────────────────────────────────────────────

st.markdown("""
<div style="animation: fadeIn 0.4s ease-out;">
    <h1 style="font-size: 2rem;">📄 Document Manager</h1>
    <p style="color: #9ca3af;">Upload, process, and manage your documents. All processing happens locally.</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Upload Section ───────────────────────────────────────────────

st.markdown("### ⬆️ Upload Documents")

col1, col2 = st.columns([3, 1])

with col1:
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=SUPPORTED_FORMATS,
        accept_multiple_files=True,
        help="Supports PDF, Word, Excel, PowerPoint, CSV, images, emails, and text files.",
    )

with col2:
    access_level = st.selectbox(
        "Access Level",
        ["public", "internal", "confidential", "restricted"],
        help="Controls who can query these documents based on their role.",
    )

if uploaded_files:
    st.markdown(f"**{len(uploaded_files)} file(s) selected**")

    if st.button("🚀 Process Documents", use_container_width=True):
        emb, vs, pipeline = get_services()

        progress = st.progress(0, text="Initializing...")
        status_container = st.container()

        for i, uploaded_file in enumerate(uploaded_files):
            progress_pct = (i / len(uploaded_files))
            progress.progress(progress_pct, text=f"Processing: {uploaded_file.name}")

            # Save to temp file
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                with status_container:
                    with st.spinner(f"📊 Processing {uploaded_file.name}..."):
                        async def process_uploaded_document():
                            from models.database import async_session_factory, init_db
                            from services.audit_service import AuditService

                            await init_db()
                            async with async_session_factory() as db:
                                result = await pipeline.process_document_sync(
                                    file_path=tmp_path,
                                    original_filename=uploaded_file.name,
                                    org_id=st.session_state.org_id,
                                    user_id=st.session_state.user["id"],
                                    access_level=access_level,
                                    db=db,
                                )
                                await AuditService.log_event(
                                    db,
                                    user_id=st.session_state.user["id"],
                                    user_email=st.session_state.user.get("email"),
                                    org_id=st.session_state.org_id,
                                    action="upload",
                                    response_text=f"Uploaded {uploaded_file.name}",
                                    source_documents=[uploaded_file.name],
                                )
                                return result

                        result = run_async(
                            process_uploaded_document()
                        )

                    st.success(
                        f"✅ **{uploaded_file.name}** — "
                        f"{result['chunks']} chunks indexed"
                    )

            except Exception as e:
                with status_container:
                    st.error(f"❌ **{uploaded_file.name}** — {str(e)}")

            finally:
                os.unlink(tmp_path)

        progress.progress(1.0, text="✅ All documents processed!")
        st.balloons()


# ── Document List ────────────────────────────────────────────────

st.divider()
st.markdown("### 📋 Your Documents")

try:
    async def load_documents():
        from sqlalchemy import select
        from models.database import async_session_factory, init_db
        from models.document import Document

        await init_db()
        async with async_session_factory() as db:
            result = await db.execute(
                select(Document)
                .where(Document.org_id == st.session_state.org_id)
                .order_by(Document.created_at.desc())
            )
            return result.scalars().all()

    documents = run_async(load_documents())

    if documents:
        # Show stats
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Documents", len(documents))
        with c2:
            st.metric("Total Chunks", sum(doc.chunk_count or 0 for doc in documents))

        for doc in documents:
            info = {
                "id": doc.id,
                "filename": doc.original_filename,
                "chunks": doc.chunk_count or 0,
                "access_level": doc.access_level.value if hasattr(doc.access_level, "value") else str(doc.access_level),
                "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
            }
            if render_document_row(st, info, delete_key=f"del_{info['id']}"):
                async def delete_document():
                    from models.database import async_session_factory, init_db
                    from services.audit_service import AuditService

                    await init_db()
                    async with async_session_factory() as db:
                        _, vs, pipeline = get_services()
                        await pipeline.delete_document(
                            info["id"],
                            st.session_state.org_id,
                            db=db,
                        )
                        await AuditService.log_event(
                            db,
                            user_id=st.session_state.user["id"],
                            user_email=st.session_state.user.get("email"),
                            org_id=st.session_state.org_id,
                            action="delete",
                            response_text=f"Deleted {info['filename']}",
                            source_documents=[info["filename"]],
                        )

                run_async(delete_document())
                st.success("Document deleted!")
                st.rerun()
    else:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #6b7280;">
            <p style="font-size: 3rem; margin-bottom: 0.5rem;">📭</p>
            <p style="font-size: 1.1rem;">No documents yet</p>
            <p style="font-size: 0.85rem;">Upload some documents above to get started.</p>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.markdown("""
    <div style="text-align: center; padding: 3rem; color: #6b7280;">
        <p style="font-size: 3rem; margin-bottom: 0.5rem;">📭</p>
        <p style="font-size: 1.1rem;">No documents yet</p>
        <p style="font-size: 0.85rem;">Upload some documents above to get started.</p>
    </div>
    """, unsafe_allow_html=True)
