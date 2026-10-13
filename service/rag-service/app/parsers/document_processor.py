from app.parsers.document_parser import parse_document
from app.parsers.text_cleaner import clean_text
from app.parsers.text_chunker import chunk_text


def process_document(
    content: bytes,
    content_type: str,
) -> list[str]:
    """Extract, clean, and chunk a document."""

    extracted_text = parse_document(
        content=content,
        content_type=content_type,
    )

    cleaned_text = clean_text(extracted_text)

    chunks = chunk_text(
        text=cleaned_text,
        chunk_size=1000,
        chunk_overlap=200,
    )

    if not chunks:
        raise ValueError("Document produced no text chunks")

    return chunks