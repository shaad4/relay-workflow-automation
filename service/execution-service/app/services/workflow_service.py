from app.grpc.workflow_client import WorkflowClient


async def load_workflow_definition(
    workflow_id: str,
    version_id: str,
    workspace_id: str,
):
    client = WorkflowClient()

    try:
        response = await client.get_workflow_definition(
            workflow_id=workflow_id,
            version_id=version_id,
            workspace_id=workspace_id,
        )

        return response

    finally:
        await client.close()