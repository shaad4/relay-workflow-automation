
import os

import grpc

from app.grpc.generated.rag import rag_pb2
from app.grpc.generated.rag import rag_pb2_grpc


RAG_SERVICE_ADDRESS = os.getenv(
    "RAG_GRPC_ADDRESS",
    "rag-service:50056",
)


class RagClient:

    def __init__(self):
        self.channel = grpc.aio.insecure_channel(
            RAG_SERVICE_ADDRESS
        )

        self.stub = (
            rag_pb2_grpc.RagInternalServiceStub(
                self.channel
            )
        )

    async def retrieve(
        self,
        workspace_id: str,
        knowledge_base_id: str,
        query: str,
        top_k: int = 5,
    ) -> rag_pb2.RetrieveResponse:
        """Retrieve relevant chunks from RAG Service."""

        # 1. Validate workspace and knowledge base
        if not workspace_id or not knowledge_base_id:
            raise ValueError(
                "Workspace and knowledge base IDs are required"
            )

        # 2. Validate query
        query = query.strip()

        if not query:
            raise ValueError(
                "RAG query cannot be empty"
            )

        if len(query) > 2000:
            raise ValueError(
                "RAG query cannot exceed 2000 characters"
            )

        # 3. Validate top_k
        if not 1 <= top_k <= 20:
            raise ValueError(
                "top_k must be between 1 and 20"
            )

        # 4. Build protobuf request
        request = rag_pb2.RetrieveRequest(
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=top_k,
        )

        # 5. Execute gRPC request
        try:
            return await self.stub.Retrieve(
                request,
                timeout=20.0,
            )
        
        except grpc.aio.AioRpcError as exc:
            status = exc.code()

            # Temporary errors: preserve gRPC status for retries.
            if status in {
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED,
            }:
                raise

            # Permanent errors: do not retry.
            if status == grpc.StatusCode.NOT_FOUND:
                raise ValueError(
                    "Knowledge base not found"
                ) from exc

            if status == grpc.StatusCode.INVALID_ARGUMENT:
                raise ValueError(
                    "Invalid RAG retrieval request"
                ) from exc

            raise RuntimeError(
                "RAG retrieval failed"
            ) from exc

    async def close(self):
        """Close the gRPC channel."""
        await self.channel.close()
