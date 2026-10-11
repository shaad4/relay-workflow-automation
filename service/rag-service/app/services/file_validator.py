from fastapi import HTTPException, UploadFile


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
}


async def validate_document(file: UploadFile) -> bytes:
    filename = file.filename or ""

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    content_type = file.content_type

    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported",
        )

    expected_extension = ALLOWED_TYPES[content_type]

    if not filename.lower().endswith(expected_extension):
        raise HTTPException(
            status_code=400,
            detail="File extension does not match content type",
        )

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

    if content_type == "application/pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file",
            )

    return content