from models.document import AccessLevel
from models.user import Role
from services.retrieval_service import ROLE_ACCESS_MAP, RetrievalResult


def test_role_access_map_covers_expected_levels():
    assert ROLE_ACCESS_MAP[Role.ADMIN.value] == [
        AccessLevel.PUBLIC.value,
        AccessLevel.INTERNAL.value,
        AccessLevel.CONFIDENTIAL.value,
        AccessLevel.RESTRICTED.value,
    ]
    assert ROLE_ACCESS_MAP[Role.VIEWER.value] == [AccessLevel.PUBLIC.value]


def test_retrieval_result_to_dict():
    result = RetrievalResult(
        content="chunk text",
        score=0.91,
        doc_id="doc-1",
        filename="a.pdf",
        chunk_type="detail",
        page_number=4,
        section_title="Summary",
    )

    payload = result.to_dict()

    assert payload["doc_id"] == "doc-1"
    assert payload["filename"] == "a.pdf"
    assert payload["page_number"] == 4
