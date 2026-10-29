import grpc

from app.config import grpc_bind_address
from app.grpc.generated.workflow import workflow_pb2_grpc
from app.grpc.workflow_server import WorkflowInternalService


async def start_grpc_server():
    server = grpc.aio.server()

    workflow_pb2_grpc.add_WorkflowInternalServiceServicer_to_server(
        WorkflowInternalService(),
        server,
    )

    port = server.add_insecure_port(grpc_bind_address(50052))
    if port == 0:
        raise RuntimeError("Failed to bind internal gRPC port")

    await server.start()

    return server
