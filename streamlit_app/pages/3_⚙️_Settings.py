"""
Settings page for model, retrieval, and system configuration guidance.
"""

import os
import platform
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.settings import get_settings


st.set_page_config(page_title="PrivateGPT - Settings", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the main page.")
    st.stop()

st.markdown(
    """
<style>
    .stApp { background: #f5f1e8 !important; }
    [data-testid="stSidebar"] { background: #ebe4d8 !important; }
</style>
""",
    unsafe_allow_html=True,
)

settings = get_settings()

provider_labels = {
    "llama_cpp": "Llama.cpp (GGUF)",
    "ollama": "Ollama",
    "huggingface": "HuggingFace Transformers",
}

st.title("Settings")
st.caption("Review the current `.env`-driven configuration for local and production deployments.")

st.subheader("LLM Configuration")

selected_provider = st.selectbox(
    "Default Provider",
    options=list(provider_labels.keys()),
    index=list(provider_labels.keys()).index(settings.llm_provider)
    if settings.llm_provider in provider_labels
    else 0,
    format_func=lambda value: provider_labels[value],
    help="This page shows the active configuration. Update `.env` to persist changes.",
)

tab_llama, tab_ollama, tab_hf = st.tabs(["Llama.cpp", "Ollama", "HuggingFace"])

with tab_llama:
    st.markdown("**Best for:** fully local GGUF inference with `llama-cpp-python`.")
    col1, col2 = st.columns(2)
    with col1:
        model_path = st.text_input("Model Path", value=settings.llm_model_path)
        st.number_input("Context Length", min_value=512, max_value=8192, step=256, value=settings.llm_context_length)
        st.number_input("Max Output Tokens", min_value=64, max_value=2048, step=64, value=settings.llm_max_tokens)
    with col2:
        st.number_input("CPU Threads", min_value=1, max_value=32, value=settings.llm_n_threads)
        st.number_input("GPU Layers", min_value=0, max_value=120, value=settings.llm_n_gpu_layers)
        st.slider("Temperature", min_value=0.0, max_value=1.0, step=0.05, value=settings.llm_temperature)

    if Path(model_path).exists():
        size_mb = Path(model_path).stat().st_size / (1024 * 1024)
        st.success(f"Model found: {Path(model_path).name} ({size_mb:.0f} MB)")
    else:
        st.warning(f"Model file not found at `{model_path}`")

with tab_ollama:
    st.markdown("**Best for:** simple local model management through Ollama.")
    st.text_input("Ollama URL", value=settings.ollama_base_url)
    st.text_input("Ollama Model", value=settings.ollama_model)
    st.info("Run `ollama pull tinyllama` or another model before switching providers.")

with tab_hf:
    st.markdown("**Best for:** Transformers-based local inference on GPU infrastructure.")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Model ID", value=settings.hf_model_id)
        st.text_input("Device Map", value=settings.hf_device_map)
        st.text_input("HF Token", value=settings.hf_auth_token or "", type="password")
    with col2:
        st.checkbox("Load in 4-bit", value=settings.hf_load_in_4bit)
        st.checkbox("Load in 8-bit", value=settings.hf_load_in_8bit)
        st.checkbox("Trust Remote Code", value=settings.hf_trust_remote_code)

st.subheader("Embedding and Retrieval")

embedding_models = {
    "all-MiniLM-L6-v2": "fast general-purpose encoder",
    "all-mpnet-base-v2": "higher quality general-purpose encoder",
    "paraphrase-multilingual-MiniLM-L12-v2": "multilingual support",
}

st.selectbox(
    "Embedding Model",
    options=list(embedding_models.keys()),
    index=list(embedding_models.keys()).index(settings.embedding_model_name)
    if settings.embedding_model_name in embedding_models
    else 0,
    format_func=lambda value: f"{value} - {embedding_models[value]}",
)

col1, col2 = st.columns(2)
with col1:
    st.number_input("Chunk Size", min_value=200, max_value=3000, step=100, value=settings.chunk_size)
    st.number_input("Retrieval Top K", min_value=5, max_value=50, value=settings.retrieval_top_k)
with col2:
    st.number_input("Chunk Overlap", min_value=0, max_value=500, step=50, value=settings.chunk_overlap)
    st.number_input("Retrieval Top N", min_value=1, max_value=20, value=settings.retrieval_top_n)

st.checkbox("Enable Hierarchical Chunking", value=settings.enable_hierarchical_chunking)
st.checkbox("Enable Cross-Encoder Reranking", value=settings.enable_reranking)

st.subheader("System Information")

try:
    import psutil

    memory = psutil.virtual_memory()
    total_ram = f"{memory.total / (1024 ** 3):.1f} GB"
    used_ram = f"{memory.used / (1024 ** 3):.1f} GB"
except ImportError:
    total_ram = "N/A"
    used_ram = "N/A"

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Platform", platform.system())
    st.metric("Python", platform.python_version())
with col2:
    st.metric("Total RAM", total_ram)
    st.metric("Used RAM", used_ram)
with col3:
    st.metric("LLM Provider", provider_labels.get(selected_provider, selected_provider))
    st.metric("Environment", settings.app_env)

st.info("Settings shown here are read from `.env`. Update that file and restart the app to persist changes.")
