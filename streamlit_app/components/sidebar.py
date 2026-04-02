"""
Shared sidebar rendering for the Streamlit app.
"""


def render_sidebar(st, on_logout):
    """Render the main application sidebar."""
    with st.sidebar:
        st.markdown(
            """
        <div class="brand-header">
            <h1>PrivateGPT</h1>
            <p>Secure Document Intelligence</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.divider()

        if st.session_state.authenticated:
            user = st.session_state.user or {}
            st.markdown(f"**User**  {user.get('full_name', 'User')}")
            st.markdown(f"`{user.get('email', '')}`")
            st.markdown(
                f"""<span class="badge badge-info">{user.get('role', 'analyst').upper()}</span>""",
                unsafe_allow_html=True,
            )

            st.divider()

            if st.button("Logout", use_container_width=True):
                on_logout()
        else:
            st.info("Please log in to get started.")

        st.divider()
        st.markdown(
            """
        <div style="text-align: center; color: var(--text-muted); font-size: 0.75rem;">
            <p>All data stays on-device</p>
            <p>No cloud. No leaks.</p>
            <p style="margin-top: 0.5rem;">v1.0.0</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
