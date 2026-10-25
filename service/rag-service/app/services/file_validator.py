from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {
    ".pdf": {
        "application/pdf",
    },
    ".txt": {
        "text/plain",
    },
    ".md": {
        "text/markdown",
        "text/plain",
        "application/octet-stream",
    },
}

# Canonical MIME types used for storage
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


async def validate_document(file: UploadFile) -> bytes:
    filename = file.filename or ""

    if not filename.strip():
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    extension = Path(filename).suffix.lower()
    content_type = file.content_type or ""

    # 1. Validate extension
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, TXT and Markdown files are supported",
        )

    # 2. Validate MIME type
    if content_type not in ALLOWED_EXTENSIONS[extension]:
        raise HTTPException(
            status_code=400,
            detail="File content type does not match extension",
        )

    # 3. Read file with size limit
    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Empty files are not allowed",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 10 MB",
        )

    # 4. Validate PDF signature
    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file",
            )

    # 5. Validate TXT / Markdown encoding
    if extension in {".txt", ".md"}:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=400,
                detail="Text files must use UTF-8 encoding",
            ) from exc

        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Document contains no readable text",
            )

    return content
