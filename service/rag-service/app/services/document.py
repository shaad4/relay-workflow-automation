
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.models.document import Document
from app.repositories.document import DocumentRepository
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.services.file_validator import (
    CONTENT_TYPES,
    validate_document,
)
from app.storage.supabase_storage import SupabaseStorage


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

    async def upload_document(
        self,
        file: UploadFile,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> Document:

        # 1. Validate knowledge base ownership
        await self.validate_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        # 2. Validate uploaded file
        content = await validate_document(file)

        # 3. Generate document identity and storage path
        document_id = uuid.uuid4()
        filename = file.filename or ""
        extension = Path(filename).suffix.lower()

        # Normalize MIME type for PDF, TXT and Markdown
        normalized_content_type = CONTENT_TYPES[extension]

        storage_path = (
            f"workspaces/{workspace_id}/"
            f"knowledge-bases/{knowledge_base_id}/"
            f"documents/{document_id}{extension}"
        )

        # 4. Create durable uploading record
        try:
            document = await self.repository.create(
                document_id=document_id,
                workspace_id=workspace_id,
                knowledge_base_id=knowledge_base_id,
                filename=filename,
                content_type=normalized_content_type,
                file_size=len(content),
                storage_path=storage_path,
                status="uploading",
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        # 5. Upload original file to Supabase Storage
        try:
            await run_in_threadpool(
                self.storage.upload,
                file_content=content,
                storage_path=storage_path,
                content_type=normalized_content_type,
            )

        except Exception:
            # Preserve uploading status for future recovery.
            # A timeout does not prove the remote upload failed.
            await self.db.rollback()
            raise

        # 6. Mark document pending for ingestion
        try:
            await self.repository.update_status(
                document=document,
                status="pending",
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            # Preserve uploading record for future recovery.
            raise

        return document


    async def list_documents(
        self,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> list[Document]:
        """List documents belonging to a knowledge base."""

        # Verify knowledge base belongs to workspace
        await self.validate_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        # Retrieve documents
        return await self.repository.list_by_knowledge_base(
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
        )


    
    async def delete_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> bool:
        """Delete a document and its associated storage object."""

        # 1. Verify knowledge base ownership
        await self.validate_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        # 2. Retrieve document
        document = await self.repository.get_by_id(
            document_id=document_id,
            workspace_id=workspace_id,
        )

        if (
            document is None
            or document.knowledge_base_id != knowledge_base_id
        ):
            return False

        # 3. Prevent deletion during active ingestion
        if document.status in {
            "uploading",
            "parsing",
            "chunking",
            "embedding",
        }:
            raise HTTPException(
                status_code=409,
                detail="Document is currently processing",
            )

        # 4. Delete original file from Supabase
        try:
            await run_in_threadpool(
                self.storage.delete,
                document.storage_path,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to delete document from storage",
            ) from exc

        # 5. Delete database record
        try:
            deleted = await self.repository.delete(
                document_id=document_id,
                workspace_id=workspace_id,
                knowledge_base_id=knowledge_base_id,
            )

            if not deleted:
                await self.db.rollback()
                return False

            await self.db.commit()
            return True

        except Exception:
            await self.db.rollback()
            raise

    
    async def retry_document(
        self,
        document_id: uuid.UUID,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
    ) -> bool:
        """Reset a failed document to pending for reprocessing."""

        # 1. Validate knowledge base ownership
        await self.validate_knowledge_base(
            knowledge_base_id=knowledge_base_id,
            workspace_id=workspace_id,
        )

        # 2. Retrieve the document
        document = await self.repository.get_by_id(
            document_id=document_id,
            workspace_id=workspace_id,
        )

        if (
            document is None
            or document.knowledge_base_id != knowledge_base_id
        ):
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        # 3. Only failed documents can be retried
        if document.status != "failed":
            raise HTTPException(
                status_code=409,
                detail="Only failed documents can be retried",
            )

        # 4. Atomically reset failed -> pending
        try:
            reset = await self.repository.reset_failed_document(
                document_id=document_id,
                workspace_id=workspace_id,
            )

            if not reset:
                await self.db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Document is no longer eligible for retry",
                )

            await self.db.commit()

            return True

        except Exception:
            await self.db.rollback()
            raise

