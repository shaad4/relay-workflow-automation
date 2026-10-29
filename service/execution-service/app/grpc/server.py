import grpc

from app.config import grpc_bind_address
from app.grpc.execution_server import ExecutionInternalService
from app.grpc.generated.execution import approval_lifecycle_pb2_grpc


async def start_grpc_server():
    server = grpc.aio.server()
    approval_lifecycle_pb2_grpc.add_ExecutionInternalServiceServicer_to_server(
        ExecutionInternalService(),
        server,
    )
    port = server.add_insecure_port(grpc_bind_address(50055))
    if port == 0:
        raise RuntimeError("Failed to bind internal gRPC port")
    await server.start()
    return server
