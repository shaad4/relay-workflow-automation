def extract_text(content: bytes) -> str:
    """Extract UTF-8 text from a TXT document."""

    if not content:
        raise ValueError("Document is empty")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Document must contain valid UTF-8 text") from exc

    if not text.strip():
        raise ValueError("Document contains no readable text")

    return text
