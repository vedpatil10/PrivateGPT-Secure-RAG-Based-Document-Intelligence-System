"""
Per-tenant FAISS vector store management.
Supports add/remove/search with metadata mapping, persistent save/load,
and tenant-isolated indexes.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np
import faiss

from config.settings import get_settings

logger = logging.getLogger("privategpt.vectorstore")


class TenantVectorStore:
    """
    Manages a FAISS index for a single tenant/organization.
    Maintains a parallel metadata store mapping vector IDs to chunk info.
    """

    def __init__(self, org_id: str, dimension: int):
        self.org_id = org_id
        self.dimension = dimension
        self._index: Optional[faiss.Index] = None
        self._metadata: List[Dict] = []  # Parallel array: metadata[i] ↔ vector[i]
        self._id_counter = 0

    @property
    def index(self) -> faiss.Index:
        if self._index is None:
            self._index = faiss.IndexFlatIP(self.dimension)  # Inner product (for normalized vectors = cosine)
        return self._index

    @property
    def size(self) -> int:
        return self.index.ntotal

    def add_vectors(
        self,
        vectors: np.ndarray,
        metadatas: List[Dict],
    ) -> List[str]:
        """
        Add vectors with associated metadata.
        Returns list of generated chunk IDs.
        """
        if len(vectors) == 0:
            return []

        vectors = np.array(vectors, dtype=np.float32)
        if vectors.ndim == 1:
            vectors = vectors.reshape(1, -1)

        # Normalize for cosine similarity via inner product
        faiss.normalize_L2(vectors)

        chunk_ids = []
        for meta in metadatas:
            chunk_id = f"{self.org_id}_{self._id_counter}"
            meta["_chunk_id"] = chunk_id
            meta["_vector_idx"] = self.index.ntotal + len(chunk_ids)
            chunk_ids.append(chunk_id)
            self._metadata.append(meta)
            self._id_counter += 1

        self.index.add(vectors)
        logger.info(f"Added {len(vectors)} vectors to tenant {self.org_id} (total: {self.size})")

        return chunk_ids

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 20,
        access_filter: Optional[List[str]] = None,
    ) -> List[Tuple[Dict, float]]:
        """
        Search for similar vectors. Returns list of (metadata, score) tuples.
        Optionally filters by access level.
        """
        if self.size == 0:
            return []

        query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(query_vector)

        # Search more than needed to account for access filtering
        search_k = min(top_k * 3, self.size)
        scores, indices = self.index.search(query_vector, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue

            meta = self._metadata[idx]

            # Apply access level filtering
            if access_filter:
                chunk_access = meta.get("access_level", "public")
                if chunk_access not in access_filter:
                    continue

            results.append((meta, float(score)))

            if len(results) >= top_k:
                break

        return results

    def remove_vectors_by_doc(self, doc_id: str):
        """
        Remove all vectors belonging to a specific document.
        Rebuilds the index without those vectors (FAISS doesn't support deletion natively).
        """
        if self.size == 0:
            return

        # Find indices to keep
        keep_indices = []
        new_metadata = []

        for i, meta in enumerate(self._metadata):
            if meta.get("doc_id") != doc_id:
                keep_indices.append(i)
                new_metadata.append(meta)

        if len(keep_indices) == len(self._metadata):
            logger.info(f"No vectors found for doc {doc_id}")
            return

        removed = len(self._metadata) - len(keep_indices)

        if keep_indices:
            # Reconstruct vectors from the existing index
            all_vectors = np.zeros((self.size, self.dimension), dtype=np.float32)
            for i in range(self.size):
                all_vectors[i] = self.index.reconstruct(i)

            keep_vectors = all_vectors[keep_indices]

            # Rebuild index
            self._index = faiss.IndexFlatIP(self.dimension)
            self._index.add(keep_vectors)

            # Update metadata indices
            for i, meta in enumerate(new_metadata):
                meta["_vector_idx"] = i

            self._metadata = new_metadata
        else:
            # All vectors removed
            self._index = faiss.IndexFlatIP(self.dimension)
            self._metadata = []

        logger.info(f"Removed {removed} vectors for doc {doc_id} from tenant {self.org_id}")


class VectorStoreManager:
    """
    Manages per-tenant FAISS indexes with persistent save/load.
    """

    def __init__(self, dimension: int = None):
        settings = get_settings()
        self.index_dir = Path(settings.faiss_index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self._stores: Dict[str, TenantVectorStore] = {}

    def _get_store(self, org_id: str) -> TenantVectorStore:
        """Get or create a tenant's vector store."""
        if org_id not in self._stores:
            store = TenantVectorStore(org_id, self.dimension)
            # Try loading from disk
            self._load_store(store)
            self._stores[org_id] = store
        return self._stores[org_id]

    def add_vectors(
        self,
        org_id: str,
        vectors: np.ndarray,
        metadatas: List[Dict],
    ) -> List[str]:
        """Add vectors to a tenant's index."""
        store = self._get_store(org_id)
        return store.add_vectors(vectors, metadatas)

    def search(
        self,
        org_id: str,
        query_vector: np.ndarray,
        top_k: int = 20,
        access_filter: Optional[List[str]] = None,
    ) -> List[Tuple[Dict, float]]:
        """Search a tenant's index."""
        store = self._get_store(org_id)
        return store.search(query_vector, top_k, access_filter)

    def remove_vectors_by_doc(self, org_id: str, doc_id: str):
        """Remove vectors for a document from a tenant's index."""
        store = self._get_store(org_id)
        store.remove_vectors_by_doc(doc_id)

    def save_index(self, org_id: str):
        """Persist a tenant's FAISS index and metadata to disk."""
        store = self._get_store(org_id)
        org_dir = self.index_dir / org_id
        org_dir.mkdir(parents=True, exist_ok=True)

        index_path = str(org_dir / "index.faiss")
        meta_path = str(org_dir / "metadata.json")

        if store.size > 0:
            faiss.write_index(store.index, index_path)

        # Save metadata
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": store._metadata,
                "id_counter": store._id_counter,
                "dimension": store.dimension,
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved index for tenant {org_id}: {store.size} vectors")

    def _load_store(self, store: TenantVectorStore):
        """Load a tenant's FAISS index and metadata from disk."""
        org_dir = self.index_dir / store.org_id
        index_path = str(org_dir / "index.faiss")
        meta_path = str(org_dir / "metadata.json")

        if not org_dir.exists():
            return

        try:
            # Load metadata
            if Path(meta_path).exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                store._metadata = data.get("metadata", [])
                store._id_counter = data.get("id_counter", 0)

            # Load FAISS index
            if Path(index_path).exists():
                store._index = faiss.read_index(index_path)
                logger.info(
                    f"Loaded index for tenant {store.org_id}: "
                    f"{store.size} vectors"
                )
        except Exception as e:
            logger.error(f"Failed to load index for {store.org_id}: {e}")

    def get_tenant_stats(self, org_id: str) -> dict:
        """Get statistics for a tenant's vector store."""
        store = self._get_store(org_id)
        doc_ids = set(m.get("doc_id") for m in store._metadata)
        return {
            "total_vectors": store.size,
            "total_documents": len(doc_ids),
            "dimension": store.dimension,
        }


# ── Singleton ────────────────────────────────────────────────────

_instance: Optional[VectorStoreManager] = None


def get_vector_store(dimension: int = None) -> VectorStoreManager:
    """Get or create the singleton vector store manager."""
    global _instance
    if _instance is None:
        _instance = VectorStoreManager(dimension=dimension)
    return _instance
