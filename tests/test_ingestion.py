import pytest

from services.ingestion.loaders import get_loader
from services.ingestion.processor import clean_text


def test_clean_text_removes_control_characters_and_normalizes_spacing():
    raw = "Hello\x00   world \n\n\nNext\t\tline"

    cleaned = clean_text(raw)

    assert "\x00" not in cleaned
    assert "Hello world" in cleaned
    assert "\n\n" in cleaned


def test_get_loader_rejects_unknown_extension():
    with pytest.raises(ValueError):
        get_loader("sample.unsupported")
