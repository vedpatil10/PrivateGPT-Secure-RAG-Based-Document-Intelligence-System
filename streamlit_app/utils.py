"""
Shared Streamlit helpers for auth, async bridging, and dashboard stats.
"""

import asyncio
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_async(coro):
    """Run an async coroutine from Streamlit's synchronous execution model."""
    return asyncio.run(coro)


def is_valid_email(email: str) -> bool:
    """Lightweight email validation for Streamlit forms."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email.strip()))


def password_validation_error(password: str, confirm_password: str | None = None) -> str | None:
    """Return a user-friendly password validation message."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if password.lower() == password or password.upper() == password:
        return "Password should include a mix of upper and lower case letters."
    if not any(ch.isdigit() for ch in password):
        return "Password should include at least one number."
    if confirm_password is not None and password != confirm_password:
        return "Password and confirm password do not match."
    return None


def initialize_session_state(st):
    """Initialize the app session with consistent defaults."""
    defaults = {
        "authenticated": False,
        "user": None,
        "org_id": None,
        "access_token": None,
        "messages": [],
        "conversation_id": None,
        "documents": [],
        "embedding_service": None,
        "vector_store": None,
        "pipeline": None,
        "rag_pipeline": None,
        "models_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_authenticated_session(st, auth_result: dict) -> None:
    """Persist a successful login/register result into Streamlit session state."""
    st.session_state.authenticated = True
    st.session_state.user = auth_result["user"]
    st.session_state.org_id = auth_result["user"]["org_id"]
    st.session_state.access_token = auth_result["access_token"]


def reset_session(st) -> None:
    """Clear and reinitialize Streamlit session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    initialize_session_state(st)


async def load_dashboard_stats(org_id: str) -> dict:
    """Load lightweight dashboard stats for the current tenant."""
    from sqlalchemy import select

    from models.audit import AuditLog
    from models.database import async_session_factory, init_db
    from models.document import Document

    await init_db()
    async with async_session_factory() as db:
        doc_result = await db.execute(select(Document).where(Document.org_id == org_id))
        docs = list(doc_result.scalars().all())

        audit_result = await db.execute(
            select(AuditLog).where(
                AuditLog.org_id == org_id,
                AuditLog.action == "query",
            )
        )
        query_logs = list(audit_result.scalars().all())

        return {
            "total_documents": len(docs),
            "total_chunks": sum(doc.chunk_count or 0 for doc in docs),
            "total_queries": len(query_logs),
        }
