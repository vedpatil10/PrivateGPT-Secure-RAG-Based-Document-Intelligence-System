from services.ingestion.chunker import chunk_document


def test_chunk_document_creates_summary_and_details():
    text = ("This is a long contract summary. " * 80).strip()
    page_contents = [
        {"page_number": 1, "content": text},
        {"page_number": 2, "content": text},
    ]

    chunks = chunk_document(text, page_contents, enable_hierarchical=True)

    assert chunks
    assert chunks[0].chunk_type == "summary"
    assert any(chunk.chunk_type == "detail" for chunk in chunks)
    assert any(chunk.page_number == 1 for chunk in chunks if chunk.chunk_type == "detail")


def test_chunk_document_without_hierarchy_skips_summary():
    text = ("Detailed operational note. " * 60).strip()

    chunks = chunk_document(text, enable_hierarchical=False)

    assert chunks
    assert all(chunk.chunk_type == "detail" for chunk in chunks)
