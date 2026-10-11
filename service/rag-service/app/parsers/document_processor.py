from app.parsers.document_parser import parse_document
from app.parsers.text_cleaner import clean_text


def process_document(
    content: bytes,
    content_type: str,
) -> str:
    """Extract and normalize document text."""

    extracted_text = parse_document(
        content=content,
        content_type=content_type,
    )

    cleaned_text = clean_text(extracted_text)

    return cleaned_text