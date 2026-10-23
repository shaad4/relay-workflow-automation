"""Use real pgvector distance and independent PostgreSQL ingestion claims."""
import asyncio
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.engine import make_url

from app.db.database import DATABASE_URL, engine, AsyncSessionLocal
from app.db.base import Base
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.repositories.document import DocumentRepository
from app.repositories.document_chunk import DocumentChunkRepository


@pytest_asyncio.fixture
async def database():
    url = make_url(DATABASE_URL)
    assert url.database == 'ci_test' and url.host in {'localhost','127.0.0.1'}, 'requires isolated local ci_test'
    workspaces = [uuid4(), uuid4()]
    tables = [KnowledgeBase.__table__, Document.__table__, DocumentChunk.__table__]
    async with engine.begin() as connection:
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        await connection.run_sync(lambda connection: Base.metadata.create_all(connection, tables=tables))
    try:
        yield workspaces
    finally:
        async with AsyncSessionLocal() as session:
            for model in [DocumentChunk,Document,KnowledgeBase]:
                await session.execute(delete(model).where(model.workspace_id.in_(workspaces)))
            await session.commit()
        await engine.dispose()


async def make_document(session, workspace, status='ready'):
    kb = KnowledgeBase(id=uuid4(), workspace_id=workspace, name='Isolated test')
    session.add(kb)
    await session.flush()
    doc = await DocumentRepository(session).create(uuid4(),workspace,kb.id,'test.txt','text/plain',5,'synthetic/test.txt',status)
    return kb, doc


async def test_pgvector_ranking_limits_status_and_workspace_isolation(database):
    workspace, foreign = database
    vector = [1.0] + [0.0]*1535
    orthogonal = [0.0, 1.0] + [0.0]*1534
    async with AsyncSessionLocal() as session:
        kb,doc = await make_document(session,workspace)
        repo = DocumentChunkRepository(session)
        await repo.create_chunks(doc.id,workspace,['nearest','orthogonal'],[vector,orthogonal])
        other_kb,other_doc = await make_document(session,foreign)
        await repo.create_chunks(other_doc.id,foreign,['foreign secret'],[vector])
        pending = await DocumentRepository(session).create(uuid4(),workspace,kb.id,'pending.txt','text/plain',1,'synthetic/pending.txt','pending')
        await repo.create_chunks(pending.id,workspace,['not ready'],[vector])
        await session.commit()
        results = await repo.search_similar(workspace,kb.id,vector,2)
        assert [chunk.content for chunk,_ in results] == ['nearest','orthogonal']
        assert abs(results[0][1]) < 1e-6 and abs(results[1][1]-1) < 1e-6
        assert len(await repo.search_similar(workspace,kb.id,vector,1)) == 1
        assert await repo.search_similar(foreign,kb.id,vector,20) == []
        assert await repo.search_similar(workspace,other_kb.id,vector,20) == []


async def test_concurrent_document_ingestion_claims(database):
    workspace,_ = database
    async with AsyncSessionLocal() as session:
        _,doc = await make_document(session,workspace,'pending')
        document_id = doc.id
        await session.commit()
    async def claim():
        async with AsyncSessionLocal() as session:
            result = await DocumentRepository(session).claim_for_ingestion(document_id,workspace)
            await session.commit()
            return result
    results = await asyncio.gather(*(claim() for _ in range(10)))
    assert sum(results) == 1
    async with AsyncSessionLocal() as session:
        repo = DocumentRepository(session)
        assert (await repo.get_by_id(document_id,workspace)).status == 'parsing'
        assert await repo.get_by_id(document_id,uuid4()) is None
