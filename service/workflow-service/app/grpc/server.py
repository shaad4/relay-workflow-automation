import grpc

from app.grpc.generated.workflow import workflow_pb2_grpc
from app.grpc.workflow_server import WorkflowInternalService


async def start_grpc_server():
    server = grpc.aio.server()

    workflow_pb2_grpc.add_WorkflowInternalServiceServicer_to_server(
        WorkflowInternalService(),
        server,
    )

    server.add_insecure_port("[::]:50052")

    await server.start()

    return server