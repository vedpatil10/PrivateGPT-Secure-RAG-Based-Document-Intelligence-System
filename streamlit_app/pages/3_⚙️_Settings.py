"""
⚙️ Settings — Configure LLM, embeddings, chunking, and system parameters.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from pathlib import Path

st.set_page_config(page_title="PrivateGPT — Settings", page_icon="⚙️", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("🔒 Please log in from the main page.")
    st.stop()

# CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    .stApp { background: #0a0a0f !important; font-family: 'Inter', sans-serif !important; }
    h1 { background: linear-gradient(135deg, #6366f1, #8b5cf6, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800 !important; }
    [data-testid="stSidebar"] { background: #12121a !important; }
    .stButton > button { background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; }
    .settings-card { background: #1a1a2e; border: 1px solid rgba(99, 102, 241, 0.15); border-radius: 12px; padding: 1.5rem; margin: 1rem 0; }
    code { background: rgba(99, 102, 241, 0.1) !important; color: #a78bfa !important; padding: 0.2rem 0.5rem !important; border-radius: 4px !important; }
</style>
""", unsafe_allow_html=True)

from config.settings import get_settings

settings = get_settings()

st.markdown("""
<h1 style="font-size: 2rem;">⚙️ Settings</h1>
<p style="color: #9ca3af;">Configure your LLM, embedding model, and system parameters.</p>
""", unsafe_allow_html=True)

st.divider()

# ── LLM Configuration ───────────────────────────────────────────

st.markdown("### 🧠 LLM Configuration")

tab_llama, tab_ollama = st.tabs(["🦙 Llama.cpp (GGUF)", "🐪 Ollama"])

with tab_llama:
    st.markdown("""
    **Setup Instructions for 8GB RAM:**
    1. Download a GGUF model (recommended: TinyLlama 1.1B Q4_K_M — ~700MB)
    2. Place it in the `models/` directory
    3. Configure the path below
    """)

    st.markdown("**Quick Download Commands:**")
    st.code(
        '# Option 1: TinyLlama 1.1B (fastest, ~700MB RAM)\n'
        '# Download from: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF\n'
        '# File: tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf\n\n'
        '# Option 2: Phi-2 (better quality, ~1.8GB RAM)\n'
        '# Download from: https://huggingface.co/TheBloke/phi-2-GGUF\n'
        '# File: phi-2.Q4_K_M.gguf\n\n'
        '# Option 3: Mistral 7B (best quality, ~4.4GB RAM)\n'
        '# Download from: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF\n'
        '# File: mistral-7b-instruct-v0.2.Q4_K_M.gguf',
        language="bash",
    )

    col1, col2 = st.columns(2)
    with col1:
        model_path = st.text_input(
            "Model Path",
            value=settings.llm_model_path,
            help="Path to the GGUF model file",
        )
        context_length = st.number_input(
            "Context Length",
            value=settings.llm_context_length,
            min_value=512,
            max_value=8192,
            step=256,
        )
    with col2:
        n_threads = st.number_input(
            "CPU Threads",
            value=settings.llm_n_threads,
            min_value=1,
            max_value=16,
        )
        max_tokens = st.number_input(
            "Max Output Tokens",
            value=settings.llm_max_tokens,
            min_value=64,
            max_value=2048,
            step=64,
        )

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=settings.llm_temperature,
        step=0.05,
        help="Lower = more focused/deterministic. Higher = more creative.",
    )

    # Check if model file exists
    if Path(model_path).exists():
        size_mb = Path(model_path).stat().st_size / (1024 * 1024)
        st.success(f"✅ Model found: {Path(model_path).name} ({size_mb:.0f} MB)")
    else:
        st.warning(f"⚠️ Model not found at: {model_path}")

with tab_ollama:
    st.markdown("""
    **Using Ollama (Alternative):**
    1. Install Ollama from [ollama.ai](https://ollama.ai)
    2. Run: `ollama run tinyllama`
    3. Set provider to 'ollama' below
    """)

    ollama_url = st.text_input("Ollama URL", value=settings.ollama_base_url)
    ollama_model = st.text_input("Ollama Model", value=settings.ollama_model)


st.divider()

# ── Embedding Configuration ─────────────────────────────────────

st.markdown("### 🔢 Embedding Model")

emb_models = {
    "all-MiniLM-L6-v2": "General purpose (384d, fast, ~80MB)",
    "all-mpnet-base-v2": "Higher quality (768d, ~400MB)",
    "paraphrase-multilingual-MiniLM-L12-v2": "Multilingual (384d, ~400MB)",
}

selected_emb = st.selectbox(
    "Embedding Model",
    list(emb_models.keys()),
    index=list(emb_models.keys()).index(settings.embedding_model_name)
    if settings.embedding_model_name in emb_models else 0,
    format_func=lambda x: f"{x} — {emb_models.get(x, '')}",
)

st.divider()

# ── Chunking Configuration ──────────────────────────────────────

st.markdown("### ✂️ Chunking Strategy")

col1, col2 = st.columns(2)
with col1:
    chunk_size = st.number_input(
        "Chunk Size (chars)",
        value=settings.chunk_size,
        min_value=200,
        max_value=3000,
        step=100,
    )

with col2:
    chunk_overlap = st.number_input(
        "Chunk Overlap (chars)",
        value=settings.chunk_overlap,
        min_value=0,
        max_value=500,
        step=50,
    )

hierarchical = st.checkbox(
    "Enable Hierarchical Chunking",
    value=settings.enable_hierarchical_chunking,
    help="Creates both summary-level and detail-level chunks for better retrieval.",
)

st.divider()

# ── Retrieval Configuration ──────────────────────────────────────

st.markdown("### 🔍 Retrieval Settings")

col1, col2 = st.columns(2)
with col1:
    ret_top_k = st.number_input(
        "Initial Candidates (top_k)",
        value=settings.retrieval_top_k,
        min_value=5,
        max_value=50,
    )

with col2:
    ret_top_n = st.number_input(
        "Final Results (top_n)",
        value=settings.retrieval_top_n,
        min_value=1,
        max_value=20,
    )

reranking = st.checkbox(
    "Enable Cross-Encoder Reranking",
    value=settings.enable_reranking,
    help="Uses a cross-encoder model to rerank results for better accuracy. Adds ~200ms latency.",
)

st.divider()

# ── System Info ──────────────────────────────────────────────────

st.markdown("### 📊 System Information")

import platform
try:
    import psutil
    mem = psutil.virtual_memory()
    ram_total = f"{mem.total / (1024**3):.1f} GB"
    ram_used = f"{mem.used / (1024**3):.1f} GB"
    ram_pct = f"{mem.percent}%"
except ImportError:
    ram_total = "N/A"
    ram_used = "N/A"
    ram_pct = "N/A"

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Platform", platform.system())
    st.metric("Python", platform.python_version())
with c2:
    st.metric("Total RAM", ram_total)
    st.metric("RAM Used", f"{ram_used} ({ram_pct})")
with c3:
    st.metric("LLM Provider", settings.llm_provider)
    st.metric("Environment", settings.app_env)

st.markdown("""
<div style="text-align: center; padding: 1rem; color: #6b7280; font-size: 0.8rem; margin-top: 2rem;">
    ⚠️ Settings changes in this page are for display only. 
    To persist changes, update the <code>.env</code> file and restart the app.
</div>
""", unsafe_allow_html=True)
