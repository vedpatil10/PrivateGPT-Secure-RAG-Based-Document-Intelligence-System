"""
Reusable chat-message rendering helpers.
"""


def render_chat_message(st, message: dict):
    """Render one user or assistant chat message with optional sources."""
    if message["role"] == "user":
        st.markdown(
            f'<div class="chat-user-msg">User {message["content"]}</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f'<div class="chat-ai-msg">Assistant {message["content"]}</div>',
        unsafe_allow_html=True,
    )

    if message.get("sources"):
        with st.expander(f"Sources ({len(message['sources'])})", expanded=False):
            for src in message["sources"]:
                page_info = f" Page {src['page_number']}" if src.get("page_number") else ""
                section_info = f" {src['section_title']}" if src.get("section_title") else ""
                score = f"{src['relevance_score']:.1%}" if src.get("relevance_score") else ""
                st.markdown(
                    f"""
                <div class="source-item">
                    <span class="source-filename">{src['document_name']}</span>
                    {page_info}{section_info}
                    <span style="float: right; color: #10b981;">{score}</span>
                    <br/><span style="color: #6b7280; font-size: 0.8rem;">{src['chunk_content'][:200]}...</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

    if message.get("query_time_ms"):
        st.markdown(
            f'<div class="query-time">{message["query_time_ms"]}ms</div>',
            unsafe_allow_html=True,
        )
