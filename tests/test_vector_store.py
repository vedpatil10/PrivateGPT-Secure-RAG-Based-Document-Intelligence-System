import numpy as np

from services.vector_store import TenantVectorStore


def test_tenant_vector_store_add_search_and_remove():
    store = TenantVectorStore(org_id="org-test", dimension=3)

    vectors = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    metadatas = [
        {"doc_id": "doc-1", "filename": "a.txt", "content": "alpha", "access_level": "public"},
        {"doc_id": "doc-2", "filename": "b.txt", "content": "beta", "access_level": "restricted"},
    ]

    store.add_vectors(vectors, metadatas)
    results = store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2, access_filter=["public"])

    assert len(results) == 1
    assert results[0][0]["doc_id"] == "doc-1"

    store.remove_vectors_by_doc("doc-1")
    remaining = store.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)

    assert all(meta["doc_id"] != "doc-1" for meta, _score in remaining)
