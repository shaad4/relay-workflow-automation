from app.parsers.pdf_parser import extract_pdf_text
from app.parsers.text_parser import extract_text

SUPPORTED_CONTENT_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
}


def parse_document(
    content: bytes,
    content_type: str,
) -> str:
    """Extract text based on document MIME type."""

    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError(f"Unsupported document type: {content_type}")

    if content_type == "application/pdf":
        return extract_pdf_text(content)

    return extract_text(content)
