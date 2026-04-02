"""
PrivateGPT Streamlit entrypoint with reusable auth and dashboard UI.
"""

import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.utils import (
    initialize_session_state,
    is_valid_email,
    load_dashboard_stats,
    password_validation_error,
    reset_session,
    run_async,
    set_authenticated_session,
)

st.set_page_config(
    page_title="PrivateGPT - Document Intelligence",
    page_icon="P",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    :root {
        --bg-primary: #0a0a0f;
        --bg-secondary: #12121a;
        --bg-card: #1a1a2e;
        --border-color: rgba(99, 102, 241, 0.15);
        --text-primary: #e8e8f0;
        --text-secondary: #9ca3af;
        --text-muted: #6b7280;
        --accent-gradient: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa);
    }
    .stApp {
        background: var(--bg-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .main .block-container {
        max-width: 1200px;
        padding: 2rem 1rem;
    }
    [data-testid="stSidebar"] {
        background: var(--bg-secondary) !important;
        border-right: 1px solid var(--border-color) !important;
    }
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
    }
    h1 {
        background: var(--accent-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    .stButton > button {
        background: var(--accent-gradient) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    .stTextInput > div > div > input {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 10px !important;
    }
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 12px !important;
        padding: 1rem !important;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-info { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
    .brand-header {
        text-align: center;
        padding: 1.5rem 0;
    }
</style>
""",
    unsafe_allow_html=True,
)


initialize_session_state(st)


def handle_logout():
    reset_session(st)
    st.rerun()


async def authenticate_login(email: str, password: str):
    from models.database import async_session_factory, init_db
    from services.auth_service import AuthService

    await init_db()
    async with async_session_factory() as db:
        return await AuthService.login(email, password, db)


async def authenticate_register(org_name: str, email: str, password: str, full_name: str):
    from models.database import async_session_factory, init_db
    from services.auth_service import AuthService

    await init_db()
    async with async_session_factory() as db:
        return await AuthService.register(org_name, email, password, full_name, db)


render_sidebar(st, handle_logout)


def render_auth_screen():
    col_spacer1, col_main, col_spacer2 = st.columns([1, 2, 1])

    with col_main:
        st.markdown(
            """
        <div style="text-align: center; margin: 2rem 0;">
            <h1 style="font-size: 2.5rem;">PrivateGPT</h1>
            <p style="color: #9ca3af; font-size: 1.1rem; margin-top: 0.5rem;">
                Secure RAG-Based Document Intelligence
            </p>
            <p style="color: #6b7280; font-size: 0.9rem;">
                Upload documents. Ask questions. Get cited answers. 100% private.
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["Login", "Sign Up"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="you@company.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

                if submitted:
                    if not email or not password:
                        st.error("Email and password are required.")
                    elif not is_valid_email(email):
                        st.error("Please enter a valid email address.")
                    else:
                        try:
                            result = run_async(authenticate_login(email, password))
                            set_authenticated_session(st, result)
                            st.success("Welcome back!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Sign in failed: {exc}")

        with tab_register:
            with st.form("register_form"):
                org_name = st.text_input("Organization Name", placeholder="Acme Corp")
                full_name = st.text_input("Full Name", placeholder="John Doe")
                reg_email = st.text_input("Work Email", placeholder="admin@acme.com")
                reg_password = st.text_input("Password", type="password", placeholder="Use at least 8 characters")
                reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Repeat your password")
                submitted = st.form_submit_button("Create Account", use_container_width=True)

                if submitted:
                    if not all([org_name, full_name, reg_email, reg_password, reg_confirm]):
                        st.error("Please complete all signup fields.")
                    elif not is_valid_email(reg_email):
                        st.error("Please enter a valid email address.")
                    else:
                        password_error = password_validation_error(reg_password, reg_confirm)
                        if password_error:
                            st.error(password_error)
                        else:
                            try:
                                result = run_async(
                                    authenticate_register(
                                        org_name=org_name,
                                        email=reg_email,
                                        password=reg_password,
                                        full_name=full_name,
                                    )
                                )
                                set_authenticated_session(st, result)
                                st.success("Account created! Welcome to PrivateGPT.")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Signup failed: {exc}")


def render_dashboard():
    st.markdown(
        """
    <div>
        <h1 style="font-size: 2rem; margin-bottom: 0.5rem;">Dashboard</h1>
        <p style="color: #9ca3af;">Welcome to your secure document intelligence workspace.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    total_docs = 0
    total_chunks = 0
    total_queries = len(st.session_state.messages) // 2

    try:
        stats = run_async(load_dashboard_stats(st.session_state.org_id))
        total_docs = stats["total_documents"]
        total_chunks = stats["total_chunks"]
        total_queries = stats["total_queries"]
    except Exception:
        pass

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Documents", total_docs)
    with col2:
        st.metric("Chunks", total_chunks)
    with col3:
        st.metric("Queries", total_queries)
    with col4:
        st.metric("Privacy", "100%")

    st.divider()
    st.markdown(
        """
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
        <div style="background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.05));
                    border: 1px solid rgba(99, 102, 241, 0.2);
                    border-radius: 12px; padding: 1.5rem;">
            <h3 style="font-size: 1.1rem;">Upload Documents</h3>
            <p style="color: #9ca3af; font-size: 0.85rem;">
                Go to the Documents page to upload PDFs, Word files, spreadsheets, emails, and images.
            </p>
        </div>
        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(52, 211, 153, 0.05));
                    border: 1px solid rgba(16, 185, 129, 0.2);
                    border-radius: 12px; padding: 1.5rem;">
            <h3 style="font-size: 1.1rem;">Ask Questions</h3>
            <p style="color: #9ca3af; font-size: 0.85rem;">
                Go to the Chat page for cited answers with conversation history and streaming output.
            </p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


if not st.session_state.authenticated:
    render_auth_screen()
else:
    render_dashboard()
