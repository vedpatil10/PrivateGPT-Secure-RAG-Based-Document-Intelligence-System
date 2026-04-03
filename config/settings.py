"""
PrivateGPT Settings — Centralized configuration using Pydantic Settings.
Optimized for 8GB RAM, CPU-only inference with GGUF models.
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_name: str = "PrivateGPT"
    app_env: str = "development"
    debug: bool = True

    # ── Security ─────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    encryption_key: str = "change-me-generate-with-fernet"
    rate_limit_requests_per_minute: int = 120

    # ── LLM Configuration (CPU-optimized) ────────────────────────
    llm_provider: str = "llama_cpp"  # llama_cpp | ollama | huggingface
    llm_model_path: str = str(BASE_DIR / "models" / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
    llm_context_length: int = 2048
    llm_max_tokens: int = 512
    llm_temperature: float = 0.1
    llm_n_threads: int = 4
    llm_n_gpu_layers: int = 0  # 0 = pure CPU

    # ── HuggingFace Transformers Provider ────────────────────────
    hf_model_id: str = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
    hf_auth_token: Optional[str] = None
    hf_device_map: str = "auto"
    hf_load_in_4bit: bool = False
    hf_load_in_8bit: bool = False
    hf_trust_remote_code: bool = False

    # ── Ollama (alternative provider) ────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "tinyllama"

    # ── Embedding Configuration ──────────────────────────────────
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_cache_dir: str = str(BASE_DIR / "data" / "cache" / "embeddings")
    embedding_batch_size: int = 32

    # ── Retrieval Configuration ──────────────────────────────────
    retrieval_top_k: int = 20       # Initial FAISS candidates
    retrieval_top_n: int = 5        # After reranking
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    enable_reranking: bool = True

    # ── Chunking Configuration ───────────────────────────────────
    chunk_size: int = 1000
    chunk_overlap: int = 200
    enable_hierarchical_chunking: bool = True
    summary_max_length: int = 500

    # ── Database ─────────────────────────────────────────────────
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'privategpt.db'}"

    # ── Storage Paths ────────────────────────────────────────────
    upload_dir: str = str(BASE_DIR / "data" / "uploads")
    faiss_index_dir: str = str(BASE_DIR / "data" / "faiss_indexes")
    cache_dir: str = str(BASE_DIR / "data" / "cache")

    def ensure_directories(self):
        """Create all required data directories."""
        dirs = [
            self.upload_dir,
            self.faiss_index_dir,
            self.cache_dir,
            self.embedding_cache_dir,
            str(BASE_DIR / "models"),
        ]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
