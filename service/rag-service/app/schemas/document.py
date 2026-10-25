import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    status: str
    error_message: str | None
    created_at: datetime
