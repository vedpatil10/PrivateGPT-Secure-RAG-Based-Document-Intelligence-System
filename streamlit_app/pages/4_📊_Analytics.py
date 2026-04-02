"""
Analytics dashboard backed by persisted audit and document data.
"""

import asyncio
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

st.set_page_config(page_title="PrivateGPT — Analytics", page_icon="📊", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("🔒 Please log in from the main page.")
    st.stop()


def run_async(coro):
    """Run async work from Streamlit."""
    return asyncio.run(coro)


st.markdown(
    """
<style>
    .stApp { background: #0a0a0f !important; color: #e8e8f0 !important; }
    h1 { color: #e8e8f0 !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<h1 style="font-size: 2rem;">📊 Analytics Dashboard</h1>
<p style="color: #9ca3af;">Usage, document activity, and audit-backed query behavior for your tenant.</p>
""",
    unsafe_allow_html=True,
)


async def load_analytics():
    from sqlalchemy import select

    from models.audit import AuditLog
    from models.database import async_session_factory, init_db
    from services.analytics_service import AnalyticsService

    await init_db()
    async with async_session_factory() as db:
        usage = await AnalyticsService.get_usage_stats(
            org_id=st.session_state.org_id,
            db=db,
            days=30,
        )
        audit_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.org_id == st.session_state.org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(20)
        )
        return usage, list(audit_result.scalars().all())


usage, audit_logs = run_async(load_analytics())

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Queries", usage["total_queries"])
with col2:
    st.metric("Documents", usage["total_documents"])
with col3:
    st.metric("Chunks", usage["total_chunks"])
with col4:
    st.metric("Avg Latency", f'{usage["avg_response_time_ms"]} ms')

col5, col6 = st.columns(2)
with col5:
    st.metric("No-context Queries", usage["no_context_queries"])
with col6:
    st.metric("Failed Query Rate", f'{usage["failed_query_rate"]}%')

st.divider()
st.markdown("### Most Queried Documents")
if usage["most_queried_documents"]:
    for item in usage["most_queried_documents"]:
        st.markdown(
            f"- `{item['document_name']}` — {item['query_count']} queries"
        )
else:
    st.info("No document-level query analytics yet.")

st.divider()
st.markdown("### Query Volume by Day")
if usage["query_volume_by_day"]:
    st.table(usage["query_volume_by_day"])
else:
    st.info("No recent query activity yet.")

st.divider()
st.markdown("### Recent Audit Log")
if audit_logs:
    st.table(
        [
            {
                "When": str(log.created_at),
                "User": log.user_email or log.user_id,
                "Action": log.action,
                "Duration ms": log.duration_ms,
                "Query": (log.query_text or "")[:120],
            }
            for log in audit_logs
        ]
    )
else:
    st.info("No audit log entries yet.")
