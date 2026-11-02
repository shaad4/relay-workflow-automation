from app.config import integer

AI_REQUEST_TIMEOUT_SECONDS = integer("AI_REQUEST_TIMEOUT_SECONDS", 60)

if not 1 <= AI_REQUEST_TIMEOUT_SECONDS <= 300:
    raise ValueError("AI_REQUEST_TIMEOUT_SECONDS must be between 1 and 300")
