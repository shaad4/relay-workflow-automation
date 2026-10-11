import uuid
from pathlib import Path
from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.services.file_validator import validate_document
from app.storage.supabase_storage import SupabaseStorage

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document import DocumentRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository


class DocumentService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = DocumentRepository(db)
        self.knowledge_base_repository = KnowledgeBaseRepository(db)
        self.storage = SupabaseStorage()


    async def validate_knowledge_base(
        self,
        knowledge_base_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> None:

        knowledge_base = await self.knowledge_base_repository.get_by_id(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        if knowledge_base is None:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base not found",
            )

    async def upload_to_storage(
        self,
        file: UploadFile,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> tuple[str, int]:

        content = await validate_document(file)

        extension = Path(file.filename).suffix.lower()

        storage_path = (
            f"workspaces/{workspace_id}/"
            f"knowledge-bases/{knowledge_base_id}/"
            f"documents/{document_id}{extension}"
        )

        await run_in_threadpool(
            self.storage.upload,
            file_content=content,
            storage_path=storage_path,
            content_type=file.content_type,
        )

        return storage_path, len(content)