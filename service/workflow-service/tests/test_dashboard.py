import asyncio
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.workflow import Workflow
from app.routes.dashboard import summary


def test_workflow_counts_are_workspace_scoped():
    engine=create_engine('sqlite://')
    Workflow.__table__.create(engine)
    with Session(engine) as session:
        workspace,other=uuid4(),uuid4()
        for owner,status in [(workspace,'active'),(workspace,'active'),(workspace,'inactive'),(workspace,'draft'),(other,'active')]:
            session.add(Workflow(id=uuid4(),workspace_id=owner,name='Test',status=status))
        session.commit()
        class Adapter:
            async def execute(self,query): return session.execute(query)
        assert asyncio.run(summary({'workspace_id':str(workspace)},Adapter()))=={'total_workflows':4,'active_workflows':2}
        assert asyncio.run(summary({'workspace_id':str(uuid4())},Adapter()))=={'total_workflows':0,'active_workflows':0}
    engine.dispose()
