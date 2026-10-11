from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pdf_text(content: bytes) -> str:
    """Extract text from a PDF document."""

    if not content or not content.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF file")

    try:
        reader = PdfReader(BytesIO(content), strict=True)

        if reader.is_encrypted:
            raise ValueError(
                "Encrypted PDF files are not supported"
            )

        pages = []

        for page in reader.pages:
            text = page.extract_text()

            if text and text.strip():
                pages.append(text.strip())

        if not pages:
            raise ValueError(
                "PDF contains no extractable text"
            )

        return "\n\n".join(pages)

    except (PdfReadError, OSError, ValueError) as exc:
        if isinstance(exc, ValueError):
            raise

        raise ValueError(
            "Unable to read PDF document"
        ) from exc