import re


def clean_text(text: str) -> str:
    """Normalize extracted text while preserving structure."""

    if not text or not text.strip():
        raise ValueError("Document contains no readable text")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove null bytes and unwanted control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize spaces and tabs
    text = re.sub(r"[ \t]+", " ", text)

    # Remove trailing and leading spaces per line
    text = "\n".join(
        line.strip() for line in text.split("\n")
    )

    # Limit excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = text.strip()

    if not text:
        raise ValueError("Document contains no readable text")

    return text