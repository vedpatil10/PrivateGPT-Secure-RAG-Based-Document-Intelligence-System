"""
Embedding service — generates dense vector embeddings using Sentence Transformers.
Supports model swapping, batch encoding, and disk-backed caching.
"""

import logging
import hashlib
import json
import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from config.settings import get_settings

logger = logging.getLogger("privategpt.embeddings")


class EmbeddingService:
    """
    Manages embedding model loading and text encoding.
    Supports swapping to domain-specific models (medical, legal, etc.)
    """

    def __init__(self, model_name: str = None, device: str = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model_name
        self.device = device or settings.embedding_device
        self.batch_size = settings.embedding_batch_size
        self.cache_dir = Path(settings.embedding_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._model = None
        self._dimension = None

    @property
    def model(self):
        """Lazy-load the embedding model."""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self._dimension is None:
            # Encode a dummy text to discover dimension
            dummy = self.model.encode(["test"])
            self._dimension = dummy.shape[1]
        return self._dimension

    def _load_model(self):
        """Load the SentenceTransformer model."""
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model: {self.model_name} (device={self.device})")
        self._model = SentenceTransformer(
            self.model_name,
            device=self.device,
        )
        logger.info(f"Embedding model loaded. Dimension: {self.model.get_sentence_embedding_dimension()}")
        self._dimension = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """
        Encode a list of texts into dense vector embeddings.
        Uses caching to avoid re-encoding identical texts.
        """
        if not texts:
            return np.array([])

        # Check cache for each text
        cached_results = {}
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cache_key = self._cache_key(text)
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                cached_results[i] = cached
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Encode uncached texts
        if uncached_texts:
            logger.info(
                f"Encoding {len(uncached_texts)} texts "
                f"({len(cached_results)} cached)"
            )
            new_embeddings = self.model.encode(
                uncached_texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

            # Cache new embeddings
            for idx, text, embedding in zip(
                uncached_indices, uncached_texts, new_embeddings
            ):
                cache_key = self._cache_key(text)
                self._save_to_cache(cache_key, embedding)
                cached_results[idx] = embedding

        # Assemble results in order
        result = np.array([cached_results[i] for i in range(len(texts))])
        return result

    def encode_query(self, query: str) -> np.ndarray:
        """Encode a single query text. Does not cache queries."""
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embedding[0]

    def swap_model(self, new_model_name: str):
        """Hot-swap to a different embedding model (e.g., domain-specific)."""
        logger.info(f"Swapping embedding model: {self.model_name} → {new_model_name}")
        self.model_name = new_model_name
        self._model = None
        self._dimension = None
        # Force reload
        _ = self.model
        logger.info(f"Embedding model swapped to: {new_model_name}")

    def _cache_key(self, text: str) -> str:
        """Generate a cache key from text + model name."""
        combined = f"{self.model_name}:{text}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _load_from_cache(self, key: str) -> Optional[np.ndarray]:
        """Load a cached embedding from disk."""
        cache_file = self.cache_dir / f"{key}.npy"
        if cache_file.exists():
            try:
                return np.load(str(cache_file))
            except Exception:
                return None
        return None

    def _save_to_cache(self, key: str, embedding: np.ndarray):
        """Save an embedding to disk cache."""
        cache_file = self.cache_dir / f"{key}.npy"
        try:
            np.save(str(cache_file), embedding)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def clear_cache(self):
        """Clear the embedding cache."""
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(str(self.cache_dir))
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Embedding cache cleared")


# ── Singleton Instance ───────────────────────────────────────────

_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _instance
    if _instance is None:
        _instance = EmbeddingService()
    return _instance
