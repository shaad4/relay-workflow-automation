import pytest
from app.parsers.document_parser import parse_document
from app.parsers.document_processor import process_document
from app.parsers.text_chunker import chunk_text
from app.parsers.text_cleaner import clean_text


def test_clean_text_preserves_unicode_and_paragraphs():
    assert (
        clean_text("  Café\t  東京\r\n\r\n\r\n Second   paragraph \x00")
        == "Café 東京\n\nSecond paragraph"
    )


@pytest.mark.parametrize("value", ["", "  \n  ", "\x00"])
def test_clean_text_rejects_empty_content(value):
    with pytest.raises(ValueError, match="no readable text"):
        clean_text(value)


@pytest.mark.parametrize("size,overlap", [(0, 0), (-1, 0), (10, -1), (10, 10), (10, 11)])
def test_chunk_text_rejects_invalid_configuration(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("document", size, overlap)


def test_chunk_boundaries_and_overlap_preserve_content():
    text = "abcdefghijklmnopqrstuvwxyz" * 100
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert chunks[0][-20:] == chunks[1][:20]
    assert (
        "".join(chunk if index == 0 else chunk[20:] for index, chunk in enumerate(chunks)) == text
    )


def test_short_document_and_multiple_paragraphs():
    assert chunk_text("Short document", chunk_size=100, chunk_overlap=20) == ["Short document"]
    text = "First paragraph.\n\nSecond paragraph."
    assert "First paragraph" in " ".join(chunk_text(text, chunk_size=20, chunk_overlap=5))
    assert "Second paragraph" in " ".join(chunk_text(text, chunk_size=20, chunk_overlap=5))


def test_process_document_handles_synthetic_text():
    chunks = process_document("Café\r\n\r\nSecond paragraph".encode(), "text/plain")
    assert chunks == ["Café\n\nSecond paragraph"]


@pytest.mark.parametrize(
    "content,content_type", [(b"", "text/plain"), (b"\xff", "text/plain"), (b"x", "image/png")]
)
def test_parser_rejects_invalid_documents(content, content_type):
    with pytest.raises(ValueError):
        parse_document(content, content_type)
