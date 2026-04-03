import numpy as np

from services.vector_store import VectorStoreManager


def test_vector_store_infers_dimension_on_first_add():
    manager = VectorStoreManager(dimension=None)

    chunk_ids = manager.add_vectors(
        org_id="org-1",
        vectors=np.array([[0.1, 0.2, 0.3]], dtype=np.float32),
        metadatas=[{"doc_id": "doc-1", "content": "hello"}],
    )

    assert len(chunk_ids) == 1
    assert manager.dimension == 3
