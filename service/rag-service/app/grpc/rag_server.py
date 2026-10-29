import logging
from uuid import UUID

import grpc

from app.db.database import AsyncSessionLocal
from app.grpc.generated.rag import rag_pb2, rag_pb2_grpc
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)


class RagInternalServicer(rag_pb2_grpc.RagInternalServiceServicer):
    async def Retrieve(
        self,
        request: rag_pb2.RetrieveRequest,
        context: grpc.aio.ServicerContext,
    ) -> rag_pb2.RetrieveResponse:
        """Retrieve relevant document chunks."""

        # 1. Validate UUIDs
        try:
            workspace_id = UUID(request.workspace_id)
            knowledge_base_id = UUID(request.knowledge_base_id)
        except ValueError:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Invalid workspace or knowledge base ID",
            )

        # 2. Validate search query
        query = request.query.strip()

        if not query:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Search query cannot be empty",
            )

        if len(query) > 2000:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Search query exceeds 2000 characters",
            )

        # 3. Validate top_k
        if not 1 <= request.top_k <= 20:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "top_k must be between 1 and 20",
            )

        # 4. Retrieve relevant chunks
        try:
            async with AsyncSessionLocal() as db:
                service = RetrievalService(db)

                results = await service.retrieve(
                    workspace_id=workspace_id,
                    knowledge_base_id=knowledge_base_id,
                    query=query,
                    top_k=request.top_k,
                )

        except ValueError as exc:
            if str(exc) == "Knowledge base not found":
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    "Knowledge base not found",
                )

            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                str(exc),
            )

        except Exception:
            logger.exception(
                "RAG retrieval failed: workspace=%s kb=%s",
                workspace_id,
                knowledge_base_id,
            )

            await context.abort(
                grpc.StatusCode.INTERNAL,
                "RAG retrieval failed",
            )

        # 5. Build protobuf response
        return rag_pb2.RetrieveResponse(
            chunks=[
                rag_pb2.RetrievedChunk(
                    chunk_id=item["chunk_id"],
                    document_id=item["document_id"],
                    chunk_index=item["chunk_index"],
                    content=item["content"],
                    score=item["score"],
                )
                for item in results
            ]
        )


async def start_rag_grpc_server():
    """Start the internal RAG gRPC server."""

    server = grpc.aio.server()

    rag_pb2_grpc.add_RagInternalServiceServicer_to_server(
        RagInternalServicer(),
        server,
    )

    port = server.add_insecure_port("[::]:50056")

    if port == 0:
        raise RuntimeError("Failed to bind RAG gRPC port")

    await server.start()

    logger.info("RAG gRPC server started on port %s", port)

    return server
