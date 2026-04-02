"""
Reusable document list card rendering helpers.
"""


def render_document_row(st, info: dict, delete_key: str) -> bool:
    """Render a document row and return whether delete was clicked."""
    badge_class = "badge-success"
    if info["access_level"] == "restricted":
        badge_class = "badge-error"
    elif info["access_level"] == "confidential":
        badge_class = "badge-warning"
    elif info["access_level"] == "internal":
        badge_class = "badge-info"

    col_name, col_chunks, col_access, col_status, col_action = st.columns([3, 1, 1, 1, 1])

    with col_name:
        st.markdown(f"**{info['filename']}**")
    with col_chunks:
        st.markdown(f"`{info['chunks']} chunks`")
    with col_access:
        st.markdown(
            f'<span class="badge {badge_class}">{info["access_level"]}</span>',
            unsafe_allow_html=True,
        )
    with col_status:
        st.markdown(f"`{info['status']}`")
    with col_action:
        return st.button("Delete", key=delete_key, help="Delete document")
