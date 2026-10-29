from uuid import UUID

from app.grpc.rag_client import RagClient


async def execute_rag_search(
    configuration: dict,
    workspace_id: str,
) -> dict:
    """Execute a RAG Search node using the internal gRPC service."""

    if not isinstance(configuration, dict):
        raise ValueError("Invalid RAG node configuration")

    if "knowledge_base_id" in configuration and "knowledge_base" in configuration:
        if configuration["knowledge_base_id"] != configuration["knowledge_base"]:
            raise ValueError("Conflicting knowledge base identifiers")
    knowledge_base_id = (
        configuration.get("knowledge_base_id")
        if "knowledge_base_id" in configuration
        else configuration.get("knowledge_base")
    )

    if not knowledge_base_id:
        raise ValueError("Knowledge base ID is required")

    try:
        knowledge_base_id = str(UUID(str(knowledge_base_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid knowledge base ID") from exc

    query = configuration.get("query")

    if not isinstance(query, str):
        raise ValueError("RAG query must be a string")

    query = query.strip()

    if not query:
        raise ValueError("RAG query cannot be empty")

    if len(query) > 2000:
        raise ValueError("RAG query cannot exceed 2000 characters")

    # Do not send unresolved expressions to RAG Service
    if "{{" in query:
        raise ValueError("RAG query contains unresolved expressions")

    top_k = configuration.get("top_k", 5)

    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ValueError("top_k must be an integer")

    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")

    # Retrieve knowledge through internal gRPC
    client = RagClient()

    try:
        response = await client.retrieve(
            workspace_id=workspace_id,
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=top_k,
        )
    finally:
        await client.close()

    chunks = [
        {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "score": round(chunk.score, 4),
        }
        for chunk in response.chunks
    ]

    # Build readable context for downstream AI nodes
    context = "\n\n".join(f"[chunk: {chunk['chunk_id']}]\n{chunk['content']}" for chunk in chunks)

    return {
        "chunks": chunks,
        "context": context,
    }
