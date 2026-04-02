from services.rag_pipeline import RetrievalResult, RAGPipeline


class DummyRetrievalService:
    def __init__(self, results):
        self._results = results

    def retrieve(self, **_kwargs):
        return self._results


class DummyLLM:
    def generate(self, **_kwargs):
        return "Generated answer"

    def stream(self, **_kwargs):
        yield "Generated "
        yield "answer"


def test_rag_pipeline_returns_fallback_when_no_results(monkeypatch):
    pipeline = RAGPipeline()
    monkeypatch.setattr("services.rag_pipeline.get_retrieval_service", lambda: DummyRetrievalService([]))

    result = pipeline.query("What is this?", org_id="org-1")

    assert "don't have enough information" in result["answer"].lower()
    assert result["sources"] == []


def test_rag_pipeline_returns_sources(monkeypatch):
    pipeline = RAGPipeline()
    results = [
        RetrievalResult(
            content="Relevant context",
            score=0.95,
            doc_id="doc-1",
            filename="policy.pdf",
            page_number=2,
            section_title="Policy",
        )
    ]
    monkeypatch.setattr("services.rag_pipeline.get_retrieval_service", lambda: DummyRetrievalService(results))
    monkeypatch.setattr("services.rag_pipeline.get_llm_service", lambda: DummyLLM())

    result = pipeline.query("Summarize policy", org_id="org-1")

    assert result["answer"] == "Generated answer"
    assert result["sources"][0]["document_name"] == "policy.pdf"
