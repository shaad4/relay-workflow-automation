import os


AI_REQUEST_TIMEOUT_SECONDS = int(
    os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "60")
)

if not 1 <= AI_REQUEST_TIMEOUT_SECONDS <= 300:
    raise ValueError(
        "AI_REQUEST_TIMEOUT_SECONDS must be between 1 and 300"
    )